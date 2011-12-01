"""
Common functions for search-related external modules.
"""

import logging

from datetime import timedelta, datetime
from socorro.lib.datetimeutil import utc_now

import socorro.lib.external_common as extern

logger = logging.getLogger("webapi")


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
    branches -- Restrict search to a particular branch.
        Can be a string or a list of strings.
        Default is all.
    build_ids -- Restrict search to a particular build of the software.
        Can be a string or a list of strings.
        Default is all.
    reasons -- Restrict search to crashes caused by this reason.
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
    use_full_days -- Boolean, transform dates to use full days (from 00:00:00
        to 23:59:59) or keep precise datetimes.
        Default is False.
    result_number -- Number of results to get.
        Default is 100.
    result_offset -- Get results from this offset.
        Default is 0.
    """
    # Default dates
    now = utc_now()
    lastweek = now - timedelta(7)

    filters = [
        ("data_type", "signatures", "str"),
        ("terms", None, ["list", "str"]),
        ("fields", "signature", ["list", "str"]),
        ("search_mode", "default", "str"),
        ("from_date", lastweek, "datetime"),
        ("to_date", now, "datetime"),
        ("products", None, ["list", "str"]),
        ("versions", None, ["list", "str"]),
        ("os", None, ["list", "str"]),
        ("branches", None, ["list", "str"]),
        ("reasons", None, ["list", "str"]),
        ("build_ids", None, ["list", "int"]),
        ("build_from", lastweek, "datetime"),
        ("build_to", now, "datetime"),
        ("report_process", "any", "str"),
        ("report_type", "any", "str"),
        ("plugin_terms", None, ["list", "str"]),
        ("plugin_in", "name", ["list", "str"]),
        ("plugin_search_mode", "default", "str"),
        ("use_full_days", False, "bool"),
        ("result_number", 100, "int"),
        ("result_offset", 0, "int")
    ]

    params = extern.parse_arguments(filters, kwargs)

    # If there is no product nor version, use Firefox as the default product
    if not params["products"] and not params["versions"]:
        params["products"] = ["Firefox"]

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
    params["fields"] = restrict_fields(params["fields"])

    return params

def restrict_fields(fields):
    """
    Restrict fields and return them.

    Secure by allowing only some specific values. If a value is not valid
    it is simply removed. If there end up being no more fields, return a
    default one.
    """
    secured_fields = []
    # To be moved into a config file?
    authorized_fields = [
        "signature",
        "dump"
    ]

    try:
        for field in fields:
            if field in authorized_fields and field not in secured_fields:
                secured_fields.append(field)
    except TypeError:
        pass

    if len(secured_fields) == 0:
        secured_fields.append("signature")

    return secured_fields
