import socorro.lib.datetimeutil as dtutil
from datetime import timedelta, datetime

class SearchAPI(object):
    """
    Base class for the search API. Implements useful functions.
    """

    def __init__(self, config):
        """
        Default constructor
        """
        self.context = config

    def _arrayToString(self, array, separator, prefix = "", suffix = ""):
        """
        Transforms a list to a string.
        """
        return separator.join("%s%s%s" % (prefix, x, suffix) for x in array)

    def _formatParam(self, param, paramName):
        """
        Format a parameter and return a string for ES.
        """
        if ( type(param) is str or type(param) is unicode ) and param != "_all":
            param = [param]
        if param != "_all":
            param = "(" + self._arrayToString(param, " OR ", paramName+":") + ")"
        return param

    def _dateToString(self, date):
        """
        Returns a string from a datetime object.
        """
        dateFormat = "%Y-%m-%d %H:%M:%S.%f"
        return date.strftime(dateFormat)

    def _formatDate(self, date):
        """
        Take a string and returns a datetime object.
        """
        if type(date) is not datetime:
            if type(date) is list:
                date = " ".join(date)
            date = dtutil.datetimeFromISOdateString(date)
        return date
