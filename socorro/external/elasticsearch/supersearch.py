# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from elasticutils import F, S

from socorro.external import BadArgumentError
from socorro.external.elasticsearch.base import ElasticSearchBase
from socorro.lib import datetimeutil
from socorro.lib.search_common import SearchBase


HITS_WHITE_LIST = (
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


PARAM_TO_FIELD_MAPPING = {
    'build_id': 'build',
    'date': 'date_processed',
    'platform': 'os_name',
    'platform_version': 'os_version',
    'plugin_name': 'PluginName',
    'plugin_filename': 'PluginFilename',
    'plugin_version': 'PluginVersion',
    'winsock_lsp': 'Winsock_LSP',
}


FIELD_TO_PARAM_MAPPING = dict(
    (PARAM_TO_FIELD_MAPPING[x], x) for x in PARAM_TO_FIELD_MAPPING
)


FIELDS_WITH_FULL_VERSION = [
    'email',
    'reason',
    'signature',
    'url',
    'user_comments',
    'PluginFilename',
    'PluginName',
    'PluginVersion',
]


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
        search = search.indexes(indexes)
        search = search.doctypes(self.config.elasticsearch_doctype)

        # Create filters.
        filters = F()

        for field, sub_params in params.items():
            for param in sub_params:
                name = PARAM_TO_FIELD_MAPPING.get(param.name, param.name)

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
                        args['%s' % name] = param.value[0]
                    else:
                        args['%s__in' % name] = param.value
                elif param.operator == '=':
                    # is exactly
                    args['%s.full' % name] = param.value
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
                    # not supported, and we should raise an error about that
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
                    # That is not a known field, we can't facet on it
                    raise BadArgumentError(
                        'Unknown field "%s", cannot facet on it' % value
                    )

                field_name = PARAM_TO_FIELD_MAPPING.get(value, value)
                if filter_.data_type == 'str':
                    # If the param is a string, that means what matters is
                    # the full string, and not its individual terms
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
        for hit in search.values_dict(*HITS_WHITE_LIST):
            for field in FIELD_TO_PARAM_MAPPING:
                if field in hit:
                    new_field = FIELD_TO_PARAM_MAPPING[field]
                    hit[new_field] = hit[field]
            hits.append(hit)

        return {
            'hits': hits,
            'total': search.count(),
            'facets': search.facet_counts(),
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

        indexes = self.generate_list_of_indexes(start_date, end_date)
        return ','.join(indexes)
