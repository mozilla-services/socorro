# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Common functions for search-related external modules.
"""

import datetime

import socorro.lib.external_common as extern
from socorro.lib import datetimeutil
from socorro.external import BadArgumentError, MissingArgumentError


"""Operators description:
     * '' -> 'has one of the terms'
     * '=' -> 'is exactly'
     * '~' -> 'contains'
     * '$' -> 'starts with'
     * '^' -> 'ends with'
     * '>=' -> 'greater or equal'
     * '<=' -> 'lower or equal'
     * '>' -> 'greater'
     * '<' -> 'lower'
     * '__null__' -> 'is null'
     * '!' -> 'not' (prefix)

    Note: the order of operators matters, largest operators should be first.
    For example, if '<' is before '<=', the latter will never be caught,
    leading to values starting with an '=' sign when they should not.
"""
OPERATOR_NOT = '!'
OPERATORS_BASE = ['']
OPERATORS_STRING = ['__null__', '=', '~', '$', '^']
OPERATORS_NUMBER = ['>=', '<=', '<', '>']
OPERATORS_MAP = {
    'str': OPERATORS_STRING + OPERATORS_BASE,
    'int': OPERATORS_NUMBER + OPERATORS_BASE,
    'date': OPERATORS_NUMBER,
    'datetime': OPERATORS_NUMBER,
    'enum': OPERATORS_BASE,
    'default': OPERATORS_BASE,
}


class SearchParam(object):
    def __init__(
        self,
        name,
        value,
        operator=None,
        data_type=None,
        operator_not=False
    ):
        self.name = name
        self.value = value
        self.operator = operator
        self.data_type = data_type
        self.operator_not = operator_not


class SearchFilter(object):
    def __init__(self, name, default=None, data_type='enum', mandatory=False):
        self.name = name
        self.default = default
        self.data_type = data_type
        self.mandatory = mandatory


class SearchBase(object):
    filters = [
        # Processed crash keys.
        SearchFilter('address', data_type='str'),
        SearchFilter('app_notes'),
        SearchFilter('build_id', data_type='int'),
        SearchFilter('cpu_info'),
        SearchFilter('cpu_name'),
        SearchFilter('date', data_type='datetime'),
        SearchFilter('distributor'),
        SearchFilter('distributor_version'),
        SearchFilter('dump'),
        SearchFilter('email', data_type='str'),
        SearchFilter('flash_version'),
        SearchFilter('hang_type'),
        SearchFilter('install_age', data_type='int'),
        SearchFilter('java_stack_trace'),
        SearchFilter('last_crash', data_type='int'),
        SearchFilter('platform'),
        SearchFilter('platform_version'),
        SearchFilter('plugin_filename', data_type='str'),
        SearchFilter('plugin_name', data_type='str'),
        SearchFilter('plugin_version'),
        SearchFilter('processor_notes'),
        SearchFilter('process_type'),
        SearchFilter('product'),
        SearchFilter('productid'),
        SearchFilter('reason', data_type='str'),
        SearchFilter('release_channel'),
        SearchFilter('signature', data_type='str'),
        SearchFilter('topmost_filenames'),
        SearchFilter('uptime', data_type='int'),
        SearchFilter('url', data_type='str'),
        SearchFilter('user_comments', data_type='str'),
        SearchFilter('version'),
        SearchFilter('winsock_lsp'),
        # Raw crash keys.
        SearchFilter('accessibility', data_type='bool'),
        SearchFilter('additional_minidumps'),
        SearchFilter('adapter_device_id'),
        SearchFilter('adapter_vendor_id'),
        SearchFilter('android_board'),
        SearchFilter('android_brand'),
        SearchFilter('android_cpu_abi'),
        SearchFilter('android_cpu_abi2'),
        SearchFilter('android_device'),
        SearchFilter('android_display'),
        SearchFilter('android_fingerprint'),
        SearchFilter('android_hardware'),
        SearchFilter('android_manufacturer'),
        SearchFilter('android_model'),
        SearchFilter('android_version'),
        SearchFilter('async_shutdown_timeout'),
        SearchFilter('available_page_file', data_type='int'),
        SearchFilter('available_physical_memory', data_type='int'),
        SearchFilter('available_virtual_memory', data_type='int'),
        SearchFilter('b2g_os_version'),
        SearchFilter('bios_manufacturer'),
        SearchFilter('cpu_usage_flash_process1', data_type='int'),
        SearchFilter('cpu_usage_flash_process2', data_type='int'),
        SearchFilter('em_check_compatibility', data_type='bool'),
        SearchFilter('frame_poison_base'),
        SearchFilter('frame_poison_size', data_type='int'),
        SearchFilter('is_garbage_collecting', data_type='bool'),
        SearchFilter('min_arm_version'),
        SearchFilter('number_of_processors', data_type='int'),
        SearchFilter('oom_allocation_size', data_type='int'),
        SearchFilter('plugin_cpu_usage', data_type='int'),
        SearchFilter('plugin_hang'),
        SearchFilter('plugin_hang_ui_duration', data_type='int'),
        SearchFilter('startup_time', data_type='int'),
        SearchFilter('system_memory_use_percentage', data_type='int'),
        SearchFilter('theme'),
        SearchFilter('throttleable', data_type='bool'),
        SearchFilter('throttle_rate', data_type='int'),
        SearchFilter('total_virtual_memory', data_type='int'),
        SearchFilter('useragent_locale'),
        SearchFilter('vendor'),
        # Meta parameters.
        SearchFilter('_facets', default='signature'),
        SearchFilter('_results_number', data_type='int', default=100),
        SearchFilter('_results_offset', data_type='int', default=0),
    ]

    def __init__(self, *args, **kwargs):
        self.context = kwargs.get('config')
        if 'webapi' in self.context:
            context = self.context.webapi
        else:
            # old middleware
            context = self.context
        self.config = context

    def get_parameters(self, **kwargs):
        parameters = {}

        for param in self.filters:
            values = kwargs.get(param.name, param.default)

            if values in ('', []):
                # Those values are equivalent to None here.
                # Note that we cannot use bool(), because 0 is not equivalent
                # to None in our case.
                values = None

            # all values can be a list, so we make them all lists to simplify
            if values is not None and not isinstance(values, (list, tuple)):
                values = [values]

            if values is None and param.mandatory:
                raise MissingArgumentError(param.name)
            elif values is not None:
                no_operator_param = None
                for value in values:
                    operator = None
                    operator_not = False

                    operators = OPERATORS_MAP.get(
                        param.data_type,
                        OPERATORS_MAP['default']
                    )

                    if isinstance(value, basestring):
                        if value.startswith(OPERATOR_NOT):
                            operator_not = True
                            value = value[1:]

                        for ope in operators:
                            if value.startswith(ope):
                                operator = ope
                                value = value[len(ope):]
                                break

                    # ensure the right data type
                    try:
                        value = convert_to_type(value, param.data_type)
                    except ValueError:
                        raise BadArgumentError(
                            'Bad value for parameter %s:'
                            ' "%s" is not a valid %s' %
                            (param.name, value, param.data_type)
                        )

                    if not param.name in parameters:
                        parameters[param.name] = []

                    if not operator:
                        if not no_operator_param:
                            no_operator_param = SearchParam(
                                param.name, [value], operator, param.data_type,
                                operator_not
                            )
                        else:
                            no_operator_param.value.append(value)
                    else:
                        parameters[param.name].append(SearchParam(
                            param.name, value, operator, param.data_type,
                            operator_not
                        ))

                if no_operator_param:
                    parameters[no_operator_param.name].append(
                        no_operator_param
                    )

        self.fix_date_parameter(parameters)

        return parameters

    def fix_date_parameter(self, parameters):
        """Correct the date parameter.

        If there is no date parameter, set default values. Otherwise, make
        sure there is exactly one lower bound value and one greater bound
        value.
        """
        date_range = datetime.timedelta(
            days=self.config.search_default_date_range
        )

        if not 'date' in parameters:
            now = datetimeutil.utc_now()
            lastweek = now - date_range

            parameters['date'] = []
            parameters['date'].append(SearchParam(
                'date', lastweek, '>=', 'datetime'
            ))
            parameters['date'].append(SearchParam(
                'date', now, '<=', 'datetime'
            ))
        else:
            lower_than = None
            greater_than = None
            for param in parameters['date']:
                if (
                    '<' in param.operator and (
                        not lower_than or
                        (lower_than and lower_than.value > param.value)
                    )
                ):
                    lower_than = param
                if (
                    '>' in param.operator and (
                        not greater_than or
                        (greater_than and greater_than.value < param.value)
                    )
                ):
                    greater_than = param

            # Remove all the existing parameters so we have exactly
            # one lower value and one greater value
            parameters['date'] = []

            if lower_than:
                parameters['date'].append(lower_than)
            else:
                # add a lower than that is now
                parameters['date'].append(SearchParam(
                    'date', datetimeutil.utc_now(), '<=', 'datetime'
                ))

            if greater_than:
                parameters['date'].append(greater_than)
            else:
                # add a greater than that is lower_than minus the date range
                parameters['date'].append(SearchParam(
                    'date',
                    lower_than.value - date_range,
                    '>=',
                    'datetime'
                ))

    def get_filter(self, field_name):
        for f in self.filters:
            if f.name == field_name:
                return f


def convert_to_type(value, data_type):
    if data_type == 'str' and not isinstance(value, basestring):
        value = str(value)
    # yes, 'enum' is being converted to a string
    elif data_type == 'enum' and not isinstance(value, basestring):
        value = str(value)
    elif data_type == 'int' and not isinstance(value, int):
        value = int(value)
    elif data_type == 'bool' and not isinstance(value, bool):
        value = str(value).lower() in ('true', 't', '1', 'y', 'yes')
    elif data_type == 'datetime' and not isinstance(value, datetime.datetime):
        value = datetimeutil.string_to_datetime(value)
    elif data_type == 'date' and not isinstance(value, datetime.date):
        value = datetimeutil.string_to_datetime(value).date()
    return value


def get_parameters(kwargs):
    """
    Return a dictionary of parameters with default values.

    Optional arguments:
    data_type -- Type of data to return.
        Default is None, to be determined by each service if needed.
    terms -- Terms to search for.
        Can be a string or a list of strings.
        Default is none.
    fields -- Fields to search into.
        Can be a string or a list of strings.
        Default to signature, not implemented for PostgreSQL.
    search_mode -- How to search for terms.
        Must be one of the following:
            "default", "contains", "is_exactly" or "starts_with".
        Default to "default" for ElasticSearch,
            "starts_with" for PostgreSQL.
    from_date -- Only elements after this date.
        Format must be "YYYY-mm-dd HH:ii:ss.S".
        Default is a week ago.
    to_date -- Only elements before this date.
        Format must be "YYYY-mm-dd HH:ii:ss.S".
        Default is now.
    products -- Products concerned by this search.
        Can be a string or a list of strings.
        Default is Firefox.
    os -- Restrict search to those operating systems.
        Can be a string or a list of strings.
        Default is all.
    versions -- Version of the software.
        Can be a string or a list of strings.
        Default is all.
    build_ids -- Restrict search to a particular build of the software.
        Can be a string or a list of strings.
        Default is all.
    reasons -- Restrict search to crashes caused by this reason.
        Default is all.
    release_channels -- Restrict search to crashes in this release channels.
        Default is all.
    report_type -- Retrict to a type of report.
        Can be any, crash or hang.
        Default is any.
    report_process -- How was the report processed.
        Can be any, crash or hang.
        Default is any.
    plugin_terms -- Search for terms concerning plugins.
        Can be a string or a list of strings.
        Default is none.
    plugin_in -- What field to look into.
        Can be "name" or "filename".
        Default is 'name'.
    plugin_search_mode -- How to search into plugins.
        Must be one of the following:
            "contains", "is_exactly" or "starts_with".
        Default to "contains".
    result_number -- Number of results to get.
        Default is 100.
    result_offset -- Get results from this offset.
        Default is 0.
    """
    # Default dates
    now = datetimeutil.utc_now()
    lastweek = now - datetime.timedelta(7)

    filters = [
        ("data_type", "signatures", "str"),
        ("terms", None, ["list", "str"]),
        ("signature", None, "str"),
        ("fields", "signature", ["list", "str"]),
        ("search_mode", "default", "str"),
        ("from_date", lastweek, "datetime"),
        ("to_date", now, "datetime"),
        ("products", None, ["list", "str"]),
        ("versions", None, ["list", "str"]),
        ("os", None, ["list", "str"]),
        ("reasons", None, ["list", "str"]),
        ("release_channels", None, ["list", "str"]),
        ("build_ids", None, ["list", "str"]),
        ("build_from", lastweek, "datetime"),
        ("build_to", now, "datetime"),
        ("report_process", "any", "str"),
        ("report_type", "any", "str"),
        ("plugin_terms", None, ["list", "str"]),
        ("plugin_in", "name", ["list", "str"]),
        ("plugin_search_mode", "default", "str"),
        ("result_number", 100, "int"),
        ("result_offset", 0, "int")
    ]

    params = extern.parse_arguments(filters, kwargs)

    # To be moved into a config file?
    authorized_modes = [
        "default",
        "starts_with",
        "contains",
        "is_exactly"
    ]
    if params["search_mode"] not in authorized_modes:
        params["search_mode"] = "default"
    if params["plugin_search_mode"] not in authorized_modes:
        params["plugin_search_mode"] = "default"

    # Do not search in the future and make sure we have dates where expected
    if params["to_date"] is None or params["to_date"] > now:
        params["to_date"] = now
    if params["from_date"] is None:
        params["from_date"] = lastweek

    if params["build_to"] is None or params["build_to"] > now:
        params["build_to"] = now
    if params["build_from"] is None:
        params["build_from"] = lastweek

    # Securing fields
    params['fields'] = restrict_fields(
        params['fields'],
        ['signature', 'dump']
    )
    params['plugin_in'] = restrict_fields(
        params['plugin_in'],
        ['filename', 'name']
    )

    return params


def restrict_fields(fields, authorized_fields):
    """
    Restrict fields and return them.

    Secure by allowing only some specific values. If a value is not valid
    it is simply removed. If there end up being no more fields, return a
    default one.
    """
    if not isinstance(authorized_fields, (list, tuple)):
        raise TypeError(
            'authorized_fields must be of type list or tuple, not %s' %
            type(authorized_fields)
        )
    elif not authorized_fields:
        raise ValueError('authorized_fields must not be empty')

    secured_fields = []

    try:
        for field in fields:
            if field in authorized_fields and field not in secured_fields:
                secured_fields.append(field)
    except TypeError:
        pass

    if len(secured_fields) == 0:
        # If none of the fields were allowed, use the first authorized field
        # as a default value
        secured_fields.append(authorized_fields[0])

    return secured_fields
