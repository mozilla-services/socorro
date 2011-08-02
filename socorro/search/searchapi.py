import urllib
import abc

from datetime import timedelta, datetime

import socorro.lib.datetimeutil as dtutil


class SearchAPI(object):
    """
    Base class for the search API, implements some useful functions.

    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, config):
        """
        Default contructor.

        """
        self.context = config

    @abc.abstractmethod
    def query(self):
        """
        Execute a given query against the database.

        """
        raise NotImplemented

    @abc.abstractmethod
    def search(self):
        """
        Search into the database given different parameters.

        """
        raise NotImplemented

    @abc.abstractmethod
    def report(self):
        """
        Return the results of a asked report.

        """
        raise NotImplemented

    @staticmethod
    def get_parameters(kwargs):
        """
        Optional arguments:
        for -- Terms to search for. Can be a string or a list of strings. Default is none.
        product -- Products concerned by this search. Can be a string or a list of strings. Default is Firefox.
        from -- Only elements after this date. Format must be "YYYY-mm-dd HH:ii:ss.S". Default is a week ago.
        to -- Only elements before this date. Format must be "YYYY-mm-dd HH:ii:ss.S". Default is now.
        in -- Fields to search into. Can be a string or a list of strings. Default to signature, not implemented for PostgreSQL.
        os -- Restrict search to those operating systems. Can be a string or a list of strings. Default is all.
        version -- Version of the software. Can be a string or a list of strings. Default is all.
        branches -- Restrict search to a particular branch. Can be a string or a list of strings. Default is all.
        build_id -- Restrict search to a particular build of the software. Can be a string or a list of strings. Default is all.
        crash_reason -- Restrict search to crashes caused by this reason. Default is all.
        report_type -- Retrict to a type of report. Can be any, crash or hang. Default is any.
        report_process --
        plugin_in --
        plugin_search_mode --
        plugin_term --
        search_mode -- How to search for terms. Must be one of the following: "default", "contains", "is_exactly" or "starts_with". Default to "default" for ElasticSearch, "starts_with" for PostgreSQL.
        result_number --
        result_offset --

        """
        args = {}

        # Default dates
        now = datetime.today()
        lastweek = now - timedelta(7)

        # Getting parameters that have default values
        args["terms"]               = kwargs.get("for", None)
        args["products"]            = kwargs.get("product", "Firefox")
        args["from_date"]           = kwargs.get("from", lastweek)
        args["to_date"]             = kwargs.get("to", now)
        args["fields"]              = kwargs.get("in", "signature")
        args["os"]                  = kwargs.get("os", None)
        args["version"]             = kwargs.get("version", None)
        args["branches"]            = kwargs.get("branches", None)
        args["build_id"]            = kwargs.get("build", None)
        args["reason"]              = kwargs.get("crash_reason", None)
        args["report_type"]         = kwargs.get("report_type", None)

        args["report_process"]      = kwargs.get("report_process", None)
        args["plugin_in"]           = kwargs.get("plugin_in", None)
        args["plugin_search_mode"]  = kwargs.get("plugin_search_mode", None)
        args["plugin_term"]         = kwargs.get("plugin_term", None)

        args["search_mode"]         = kwargs.get("search_mode", "default")
        # To be moved into a config file?
        authorized_modes = [
            "default",
            "starts_with",
            "contains",
            "is_exactly"
        ]
        if args["search_mode"] not in authorized_modes:
            args["search_mode"] = "default"

        args["result_number"]  = int( kwargs.get("result_number", 100) )
        args["result_offset"]  = int( kwargs.get("result_offset", 0) )

        # Handling dates
        args["from_date"] = SearchAPI.format_date(args["from_date"]) or lastweek
        args["to_date"] = SearchAPI.format_date(args["to_date"]) or now

        # Do not search in the future
        if args["to_date"] > now:
            args["to_date"] = now

        # Securing fields
        args["fields"] = SearchAPI.secure_fields(args["fields"])

        return args

    @staticmethod
    def secure_fields(fields):
        secured_fields = []
        # To be moved into a config file?
        authorized_fields = [
            "signature",
            "dump"
        ]

        if type(fields) is list:
            for field in fields:
                if authorized_fields.count(field) and not secured_fields.count(field):
                    secured_fields.append(field)
        else:
            if authorized_fields.count(fields):
                secured_fields = fields

        if len(secured_fields) == 0:
            secured_fields = "signature"

        return secured_fields


    @staticmethod
    def array_to_string(array, separator, prefix = "", suffix = ""):
        """
        Transform a list to a string.

        """
        return separator.join("%s%s%s" % (prefix, x, suffix) for x in array)

    @staticmethod
    def date_to_string(date):
        """
        Return a string from a datetime object.

        """
        date_format = "%Y-%m-%d %H:%M:%S.%f"
        return date.strftime(date_format)

    @staticmethod
    def format_date(date):
        """
        Take a string and return a datetime object.

        """
        if not date:
            return None

        if type(date) is not datetime:
            if type(date) is list:
                date = " ".join(date)
            try:
                date = dtutil.datetimeFromISOdateString(date)
            except Exception:
                date = None
        return date

    @staticmethod
    def encode_array(array):
        """
        URL-encode each element of a given array, and returns this array.

        """
        for i in xrange(len(array)):
            array[i] = urllib.quote(array[i])
        return array

    @staticmethod
    def lower(var):
        """
        Turn a string or a list of strings to lower case.
        Don't modify non-string elements.

        """
        if type(var) is list:
            for i in xrange(len(var)):
                try:
                    var[i] = var[i].lower()
                except Exception:
                    pass
        else:
            try:
                var = var.lower()
            except Exception:
                pass
        return var
