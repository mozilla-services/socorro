# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Common functions for search-related external modules.
"""

import datetime

from socorro.lib import BadArgumentError, datetimeutil
import socorro.lib.external_common as extern


"""Operators description:
     * '' -> 'has one of the terms'
     * '=' -> 'is exactly'
     * '~' -> 'contains'
     * '^' -> 'starts with'
     * '$' -> 'ends with'
     * '@' -> 'regex'
     * '>=' -> 'greater or equal'
     * '<=' -> 'lower or equal'
     * '>' -> 'greater'
     * '<' -> 'lower'
     * '__null__' -> 'is null'
     * '__true__' -> 'is true'
     * '!' -> 'not' (prefix)

    Note: the order of operators matters, largest operators should be first.
    For example, if '<' is before '<=', the latter will never be caught,
    leading to values starting with an '=' sign when they should not.
"""
OPERATOR_NOT = "!"
OPERATORS_BASE = [""]
OPERATORS_BOOL = ["__true__"]
OPERATORS_STRING = ["__null__", "=", "~", "$", "^", "@"]
OPERATORS_NUMBER = [">=", "<=", "<", ">"]
OPERATORS_MAP = {
    "str": OPERATORS_STRING + OPERATORS_BASE,
    "int": OPERATORS_NUMBER + OPERATORS_BASE,
    "date": OPERATORS_NUMBER,
    "datetime": OPERATORS_NUMBER,
    "bool": OPERATORS_BOOL,
    "enum": OPERATORS_BASE,
    "default": OPERATORS_BASE,
}


# Default date range for searches in days
DEFAULT_DATE_RANGE = 7


# Maximum date range for searches in days
MAXIMUM_DATE_RANGE = 365


# Query types of field that we can build histograms on.
HISTOGRAM_QUERY_TYPES = ("date", "number")


class SearchParam:
    def __init__(self, name, value, operator=None, data_type=None, operator_not=False):
        self.name = name
        self.value = value
        self.operator = operator
        self.data_type = data_type
        self.operator_not = operator_not


class SearchFilter:
    def __init__(self, name, default=None, data_type="enum"):
        self.name = name
        self.default = default
        self.data_type = data_type


class SearchBase:
    meta_filters = (
        SearchFilter("_aggs.product.version"),
        SearchFilter("_aggs.product.version.platform"),  # convenient for tests
        SearchFilter("_aggs.android_cpu_abi.android_manufacturer.android_model"),
        SearchFilter(
            "_columns", default=["uuid", "date", "signature", "product", "version"]
        ),
        SearchFilter("_facets", default="signature"),
        SearchFilter("_facets_size", data_type="int", default=50),
        SearchFilter("_results_number", data_type="int", default=100),
        SearchFilter("_results_offset", data_type="int", default=0),
        SearchFilter("_return_query", data_type="bool", default=False),
        SearchFilter("_sort", default=""),
    )

    def build_filters(self, fields):
        self.filters = []
        self.histogram_fields = []

        all_meta_filters = list(self.meta_filters)

        for field in fields.values():
            self.filters.append(
                SearchFilter(field["name"], data_type=field["data_validation_type"])
            )

            # Add a field to get a list of other fields to aggregate.
            all_meta_filters.append(SearchFilter("_aggs.%s" % field["name"]))

            # Generate all histogram meta filters.
            if field["query_type"] in HISTOGRAM_QUERY_TYPES:
                # Store that field in a list so we can easily use it later.
                self.histogram_fields.append(field["name"])

                # Add a field to get a list of other fields to aggregate.
                all_meta_filters.append(SearchFilter("_histogram.%s" % field["name"]))

                # Add an interval field.
                default_interval = 1
                if field["query_type"] == "date":
                    default_interval = "day"
                all_meta_filters.append(
                    SearchFilter(
                        "_histogram_interval.%s" % field["name"],
                        default=default_interval,
                    )
                )

        # Add meta parameters.
        self.filters.extend(all_meta_filters)

    def get_parameters(self, **kwargs):
        parameters = {}

        fields = kwargs["_fields"]
        assert fields
        if fields:
            self.build_filters(fields)

        for param in self.filters:
            values = kwargs.get(param.name, param.default)

            if values in ("", []):
                # Those values are equivalent to None here.
                # Note that we cannot use bool(), because 0 is not equivalent
                # to None in our case.
                values = None

            if values is None and param.default is not None:
                values = param.default

            # all values can be a list, so we make them all lists to simplify
            if values is not None and not isinstance(values, (list, tuple)):
                values = [values]

            if values is not None:
                # There should only be one parameter with no operator, and
                # we want to stack all values into it. That's why we want
                # to keep track of it.
                # Actually, we want _two_ parameters with no operator: one
                # for each possible value of "operator_not".
                no_operator_param = {True: None, False: None}

                for value in values:
                    operator = None
                    operator_not = False

                    operators = OPERATORS_MAP.get(
                        param.data_type, OPERATORS_MAP["default"]
                    )

                    if isinstance(value, str):
                        if value.startswith(OPERATOR_NOT):
                            operator_not = True
                            value = value[1:]

                        for ope in operators:
                            if value.startswith(ope):
                                operator = ope
                                value = value[len(ope) :]
                                break

                    # ensure the right data type
                    try:
                        value = convert_to_type(value, param.data_type)
                    except ValueError:
                        raise BadArgumentError(
                            param.name,
                            msg=(
                                "Bad value for parameter %s: not a valid %s"
                                % (param.name, param.data_type)
                            ),
                        )

                    if param.name not in parameters:
                        parameters[param.name] = []

                    if not operator:
                        if not no_operator_param[operator_not]:
                            no_operator_param[operator_not] = SearchParam(
                                param.name,
                                [value],
                                operator,
                                param.data_type,
                                operator_not,
                            )
                        else:
                            no_operator_param[operator_not].value.append(value)
                    else:
                        parameters[param.name].append(
                            SearchParam(
                                param.name,
                                value,
                                operator,
                                param.data_type,
                                operator_not,
                            )
                        )

                for value in no_operator_param.values():
                    if value:
                        parameters[value.name].append(value)

        self.fix_date_parameter(parameters)
        self.fix_process_type_parameter(parameters)
        self.fix_hang_type_parameter(parameters)
        self.fix_version_parameter(parameters)

        return parameters

    def fix_date_parameter(self, parameters):
        """Correct the date parameter.

        If there is no date parameter, set default values. Otherwise, make
        sure there is exactly one lower bound value and one greater bound
        value.
        """
        default_date_range = datetime.timedelta(days=DEFAULT_DATE_RANGE)
        maximum_date_range = datetime.timedelta(days=MAXIMUM_DATE_RANGE)

        if not parameters.get("date"):
            now = datetimeutil.utc_now()
            lastweek = now - default_date_range

            parameters["date"] = []
            parameters["date"].append(SearchParam("date", lastweek, ">=", "datetime"))
            parameters["date"].append(SearchParam("date", now, "<=", "datetime"))
        else:
            lower_than = None
            greater_than = None
            for param in parameters["date"]:
                if not param.operator:
                    # dates can't be a specific date
                    raise BadArgumentError(
                        "date", msg="date must have a prefix operator"
                    )
                if "<" in param.operator and (
                    not lower_than or (lower_than and lower_than.value > param.value)
                ):
                    lower_than = param
                if ">" in param.operator and (
                    not greater_than
                    or (greater_than and greater_than.value < param.value)
                ):
                    greater_than = param

            # Remove all the existing parameters so we have exactly
            # one lower value and one greater value
            parameters["date"] = []

            if not lower_than:
                # add a lower than that is now
                lower_than = SearchParam(
                    "date", datetimeutil.utc_now(), "<=", "datetime"
                )

            if not greater_than:
                # add a greater than that is lower_than minus the date range
                greater_than = SearchParam(
                    "date", lower_than.value - default_date_range, ">=", "datetime"
                )

            # Verify the date range is not too big.
            delta = lower_than.value - greater_than.value
            if delta > maximum_date_range:
                raise BadArgumentError(
                    "date", msg="Date range is bigger than %s days" % MAXIMUM_DATE_RANGE
                )

            parameters["date"].append(lower_than)
            parameters["date"].append(greater_than)

    @staticmethod
    def fix_process_type_parameter(parameters):
        """Correct the process_type parameter.

        If process_type is 'browser', replace it with a 'does not exist'
        parameter. Do nothing in all other cases.
        """
        if not parameters.get("process_type"):
            return

        new_params = []
        marked_for_deletion = []
        for index, process_type in enumerate(parameters["process_type"]):
            if "browser" in process_type.value:
                # `process_type.value` can be a string or a list of strings.
                try:
                    process_type.value.remove("browser")
                except AttributeError:
                    process_type.value = ""

                if not process_type.value:
                    marked_for_deletion.append(process_type)

                new_params.append(
                    SearchParam(
                        name="process_type",
                        value=[""],
                        data_type="enum",
                        operator="__null__",
                        operator_not=process_type.operator_not,
                    )
                )

        for param in marked_for_deletion:
            parameters["process_type"].remove(param)

        parameters["process_type"].extend(new_params)

    @staticmethod
    def fix_hang_type_parameter(parameters):
        """Correct the hang_type parameter.

        If hang_type is 'crash', replace it with '0', if it's 'hang' replace it
        with '-1, 1'.
        """
        if not parameters.get("hang_type"):
            return

        for hang_type in parameters["hang_type"]:
            new_values = []
            for val in hang_type.value:
                if val == "crash":
                    new_values.append(0)
                elif val == "hang":
                    new_values.extend([-1, 1])
                else:
                    new_values.append(val)

            hang_type.value = new_values
            hang_type.data_type = "int"

    @staticmethod
    def fix_version_parameter(parameters):
        """Correct the version parameter.

        If version is something finishing with a 'b' and operator is
        'has terms', replace the operator with 'starts with' to query all
        beta versions.

        This is applicable regardless of product, only "rapid beta" versions
        can have a trailing "b".
        """
        if not parameters.get("version"):
            return

        # Iterate on a copy so we can delete elements while looping.
        for version in list(parameters["version"]):
            if version.operator:
                # We only care about the "has terms" operator, which
                # actually is an empty string.
                continue

            new_values = []
            for val in version.value:
                if val.endswith("b"):
                    parameters["version"].append(
                        SearchParam(
                            name="version",
                            value=val,
                            data_type="str",
                            operator="^",
                            operator_not=version.operator_not,
                        )
                    )
                else:
                    new_values.append(val)

            if new_values:
                version.value = new_values
            else:
                parameters["version"].remove(version)

    def get_filter(self, field_name):
        for f in self.filters:
            if f.name == field_name:
                return f


def convert_to_type(value, data_type):
    if data_type == "str" and not isinstance(value, str):
        value = str(value)
    # yes, 'enum' is being converted to a string
    elif data_type == "enum" and not isinstance(value, str):
        value = str(value)
    elif data_type == "int" and not isinstance(value, int):
        value = int(value)
    elif data_type == "bool" and not isinstance(value, bool):
        value = str(value).lower() in ("true", "t", "1", "y", "yes")
    elif data_type == "datetime" and not isinstance(value, datetime.datetime):
        value = datetimeutil.string_to_datetime(value)
    elif data_type == "date" and not isinstance(value, datetime.date):
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
        ("result_offset", 0, "int"),
    ]

    params = extern.parse_arguments(filters, kwargs)

    # To be moved into a config file?
    authorized_modes = ["default", "starts_with", "contains", "is_exactly"]
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
    params["fields"] = restrict_fields(params["fields"], ["signature", "dump"])
    params["plugin_in"] = restrict_fields(params["plugin_in"], ["filename", "name"])

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
            "authorized_fields must be of type list or tuple, not %s"
            % type(authorized_fields)
        )
    elif not authorized_fields:
        raise ValueError("authorized_fields must not be empty")

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
