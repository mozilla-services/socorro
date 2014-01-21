# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
from elasticutils import F, S
from pyelasticsearch.exceptions import ElasticHttpNotFoundError

from socorro.external import BadArgumentError
from socorro.external.elasticsearch.base import ElasticSearchBase
from socorro.lib import datetimeutil
from socorro.lib.search_common import SearchBase


PROCESSED_CRASH_FIELDS = (
    'additional_minidumps',
    'addons',
    'addons_checked',
    'address',
    'app_notes',
    'build',
    'client_crash_date',
    'completeddatetime',
    'cpu_info',
    'cpu_name',
    'crashedThread',
    'crash_time',
    'date_processed',
    'distributor',
    'distributor_version',
    # 'dump',  # the dump is a huge piece of data, we should not return it
    'email',
    'flash_version',
    'hangid',
    'hang_type',
    'id',
    'install_age',
    'java_stack_trace',
    'last_crash',
    'os_name',
    'os_version',
    'PluginFilename',
    'PluginName',
    'PluginVersion',
    'processor_notes',
    'process_type',
    'product',
    'productid',
    'reason',
    'release_channel',
    'ReleaseChannel',
    'signature',
    'startedDateTime',
    'success',
    'topmost_filenames',
    'truncated',
    'uptime',
    'url',
    'user_comments',
    'uuid',
    'version',
    'Winsock_LSP',
)


RAW_CRASH_FIELDS = (
    'Accessibility',
    'AdapterDeviceID',
    'AdapterVendorID',
    'Android_Board',
    'Android_Brand',
    'Android_CPU_ABI',
    'Android_CPU_ABI2',
    'Android_Device',
    'Android_Display',
    'Android_Fingerprint',
    'Android_Hardware',
    'Android_Manufacturer',
    'Android_Model',
    'Android_Version',
    'AsyncShutdownTimeout',
    'AvailablePageFile',
    'AvailablePhysicalMemory',
    'AvailableVirtualMemory',
    'B2G_OS_Version',
    'BIOS_Manufacturer',
    'CpuUsageFlashProcess1',
    'CpuUsageFlashProcess2',
    'EMCheckCompatibility',
    'FramePoisonBase',
    'FramePoisonSize',
    'IsGarbageCollecting',
    'Min_ARM_Version',
    'NumberOfProcessors',
    'OOMAllocationSize',
    'PluginCpuUsage',
    'PluginHang',
    'PluginHangUIDuration',
    'StartupTime',
    'SystemMemoryUsePercentage',
    'Theme',
    'Throttleable',
    'TotalVirtualMemory',
    'Vendor',
    'additional_minidumps',
    'throttle_rate',
    'useragent_locale',
)


# This is for the sake of the consistency of our API: all keys should be
# lower case with underscores.
PARAM_TO_FIELD_MAPPING = {
    # Processed crash keys.
    'build_id': 'build',
    'date': 'date_processed',
    'platform': 'os_name',
    'platform_version': 'os_version',
    'plugin_name': 'PluginName',
    'plugin_filename': 'PluginFilename',
    'plugin_version': 'PluginVersion',
    'winsock_lsp': 'Winsock_LSP',
    # Raw crash keys.
    'accessibility': 'Accessibility',
    'adapter_device_id': 'AdapterDeviceID',
    'adapter_vendor_id': 'AdapterVendorID',
    'android_board': 'Android_Board',
    'android_brand': 'Android_Brand',
    'android_cpu_abi': 'Android_CPU_ABI',
    'android_cpu_abi2': 'Android_CPU_ABI2',
    'android_device': 'Android_Device',
    'android_display': 'Android_Display',
    'android_fingerprint': 'Android_Fingerprint',
    'android_hardware': 'Android_Hardware',
    'android_manufacturer': 'Android_Manufacturer',
    'android_model': 'Android_Model',
    'android_version': 'Android_Version',
    'async_shutdown_timeout': 'AsyncShutdownTimeout',
    'available_page_file': 'AvailablePageFile',
    'available_physical_memory': 'AvailablePhysicalMemory',
    'available_virtual_memory': 'AvailableVirtualMemory',
    'b2g_os_version': 'B2G_OS_Version',
    'bios_manufacturer': 'BIOS_Manufacturer',
    'cpu_usage_flash_process1': 'CpuUsageFlashProcess1',
    'cpu_usage_flash_process2': 'CpuUsageFlashProcess2',
    'em_check_compatibility': 'EMCheckCompatibility',
    'frame_poison_base': 'FramePoisonBase',
    'frame_poison_size': 'FramePoisonSize',
    'is_garbage_collecting': 'IsGarbageCollecting',
    'min_arm_version': 'Min_ARM_Version',
    'number_of_processors': 'NumberOfProcessors',
    'oom_allocation_size': 'OOMAllocationSize',
    'plugin_cpu_usage': 'PluginCpuUsage',
    'plugin_hang': 'PluginHang',
    'plugin_hang_ui_duration': 'PluginHangUIDuration',
    'startup_time': 'StartupTime',
    'system_memory_use_percentage': 'SystemMemoryUsePercentage',
    'theme': 'Theme',
    'throttleable': 'Throttleable',
    'total_virtual_memory': 'TotalVirtualMemory',
    'vendor': 'Vendor',
}


FIELD_TO_PARAM_MAPPING = dict(
    (PARAM_TO_FIELD_MAPPING[x], x) for x in PARAM_TO_FIELD_MAPPING
)


FIELDS_WITH_FULL_VERSION = (
    'processed_crash.cpu_info',
    'processed_crash.os_name',
    'processed_crash.product',
    'processed_crash.reason',
    'processed_crash.signature',
    'processed_crash.user_comments',
    'processed_crash.PluginFilename',
    'processed_crash.PluginName',
    'processed_crash.PluginVersion',
    'raw_crash.Android_Model',
)


BAD_INDEX_REGEX = re.compile('\[\[(.*)\] missing\]')


class SuperS(S):
    """Extend elasticutils' S class with the 'missing' filter feature from
    elasticsearch. """

    def process_filter_missing(self, key, value, action):
        return {
            'missing': {
                'field': key,
                'existence': True,
                'null_value': True,
            }
        }


class SuperSearch(SearchBase, ElasticSearchBase):

    def __init__(self, config):
        # We have multiple inheritance here, explicitly calling superclasses's
        # init is mandatory.
        # See http://freshfoo.com/blog/object__init__takes_no_parameters
        SearchBase.__init__(self, config=config)
        ElasticSearchBase.__init__(self, config=config)

    def get(self, **kwargs):
        """Return a list of results and facets based on parameters.

        The list of accepted parameters (with types and default values) is in
        socorro.lib.search_common.SearchBase
        """
        # Filter parameters and raise potential errors.
        params = self.get_parameters(**kwargs)

        # Find the indexes to use to optimize the elasticsearch query.
        indexes = self.get_indexes(params['date'])

        # Create and configure the search object.
        search = SuperS().es(
            urls=self.config.elasticsearch_urls,
            timeout=self.config.elasticsearch_timeout,
        )
        search = search.indexes(*indexes)
        search = search.doctypes(self.config.elasticsearch_doctype)

        # Create filters.
        filters = F()

        for field, sub_params in params.items():
            for param in sub_params:
                name = PARAM_TO_FIELD_MAPPING.get(param.name, param.name)
                name = self.prefix_field_name(name)

                if name.startswith('_'):
                    if name == '_results_offset':
                        results_from = param.value[0]
                    elif name == '_results_number':
                        results_number = param.value[0]
                    # Don't use meta parameters in the query.
                    continue

                if param.data_type in ('date', 'datetime'):
                    param.value = datetimeutil.date_to_string(param.value)
                elif param.data_type == 'enum':
                    param.value = [x.lower() for x in param.value]
                elif param.data_type == 'str' and not param.operator:
                    param.value = [x.lower() for x in param.value]

                args = {}
                if not param.operator:
                    # contains one of the terms
                    if len(param.value) == 1:
                        args[name] = param.value[0]
                    else:
                        args['%s__in' % name] = param.value
                elif param.operator == '=':
                    # is exactly
                    if name in FIELDS_WITH_FULL_VERSION:
                        name = '%s.full' % name
                    args[name] = param.value
                elif param.operator == '>':
                    # greater than
                    args['%s__gt' % name] = param.value
                elif param.operator == '<':
                    # lower than
                    args['%s__lt' % name] = param.value
                elif param.operator == '>=':
                    # greater than or equal to
                    args['%s__gte' % name] = param.value
                elif param.operator == '<=':
                    # lower than or equal to
                    args['%s__lte' % name] = param.value
                elif param.operator == '__null__':
                    # is null
                    args['%s__missing' % name] = param.value

                if args:
                    if param.operator_not:
                        filters &= ~F(**args)
                    else:
                        filters &= F(**args)
                    continue

                # These use a wildcard and thus need to be in a query
                # instead of a filter.
                operator_wildcards = {
                    '~': '*%s*',  # contains
                    '$': '%s*',  # starts with
                    '^': '*%s'  # ends with
                }
                if param.operator in operator_wildcards:
                    if name in FIELDS_WITH_FULL_VERSION:
                        name = '%s.full' % name
                    args['%s__wildcard' % name] = \
                        operator_wildcards[param.operator] % param.value
                    args['must_not'] = param.operator_not

                if args:
                    search = search.query(**args)
                else:
                    # If we reach this point, that means the operator is
                    # not supported, and we should raise an error about that.
                    raise NotImplementedError(
                        'Operator %s is not supported' % param.operator
                    )

        search = search.filter(filters)

        # Pagination.
        results_to = results_from + results_number
        search = search[results_from:results_to]

        # Create facets.
        processed_filters = search._process_filters(filters.filters)

        for param in params['_facets']:
            for value in param.value:
                filter_ = self.get_filter(value)
                if not filter_:
                    # That is not a known field, we can't facet on it.
                    raise BadArgumentError(
                        'Unknown field "%s", cannot facet on it' % value
                    )

                field_name = PARAM_TO_FIELD_MAPPING.get(value, value)
                field_name = self.prefix_field_name(field_name)

                if field_name in FIELDS_WITH_FULL_VERSION:
                    # If the param has a full version, that means what matters
                    # is the full string, and not its individual terms.
                    field_name += '.full'

                args = {
                    value: {
                        'terms': {
                            'field': field_name,
                            'size': self.config.facets_max_number,
                        },
                        'facet_filter': processed_filters,
                    }
                }
                search = search.facet_raw(**args)

        # Query and compute results.
        hits = []
        fields = ['processed_crash.%s' % x for x in PROCESSED_CRASH_FIELDS]
        fields.extend('raw_crash.%s' % x for x in RAW_CRASH_FIELDS)

        # We call elasticsearch with a computed list of indices, based on
        # the date range. However, if that list contains indices that do not
        # exist in elasticsearch, an error will be raised. We thus want to
        # remove all failing indices until we either have a valid list, or
        # an empty list in which case we return no result.
        while True:
            try:
                for hit in search.values_dict(*fields):
                    hits.append(self.format_field_names(hit))

                total = search.count()
                facets = search.facet_counts()
                break  # Yay! Results!
            except ElasticHttpNotFoundError, e:
                missing_index = re.findall(BAD_INDEX_REGEX, e.error)[0]
                if missing_index in indexes:
                    del indexes[indexes.index(missing_index)]
                else:
                    # Wait what? An error caused by an index that was not
                    # in the request? That should never happen, but in case
                    # it does, better know it.
                    raise

                if indexes:
                    # Update the list of indices and try again.
                    search = search.indexes(*indexes)
                else:
                    # There is no index left in the list, return an empty
                    # result.
                    hits = []
                    total = 0
                    facets = {}
                    break

        return {
            'hits': hits,
            'total': total,
            'facets': facets,
        }

    def get_indexes(self, dates):
        """Return the list of indexes to use for given dates. """
        start_date = None
        end_date = None
        for date in dates:
            if '>' in date.operator:
                start_date = date.value
            if '<' in date.operator:
                end_date = date.value

        return self.generate_list_of_indexes(start_date, end_date)

    def format_field_names(self, hit):
        new_hit = {}
        for field in hit:
            new_field = field

            if '.' in new_field:
                # Remove the prefix ("processed_crash." or "raw_crash.").
                new_field = new_field.split('.', 1)[1]

            if new_field in FIELD_TO_PARAM_MAPPING:
                new_field = FIELD_TO_PARAM_MAPPING[new_field]

            new_hit[new_field] = hit[field]

        return new_hit

    def prefix_field_name(self, field_name):
        if field_name in PROCESSED_CRASH_FIELDS:
            return 'processed_crash.%s' % field_name
        if field_name in RAW_CRASH_FIELDS:
            return 'raw_crash.%s' % field_name

        return field_name
