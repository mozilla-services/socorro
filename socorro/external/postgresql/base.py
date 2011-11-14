import logging

import socorro.database.database as db
import socorro.lib.util as util

logger = logging.getLogger("webapi")


class PostgreSQLBase(object):

    """
    Base class for PostgreSQL based service implementations.
    """

    def __init__(self, **kwargs):
        """
        Default constructor
        """
        super(PostgreSQLBase, self).__init__()

        self.context = kwargs.get("config")
        try:
            self.database = db.Database(self.context)
        except (AttributeError, KeyError):
            util.reportExceptionAndContinue(logger)

        self.connection = None

    @staticmethod
    def append_to_var(value, array):
        """
        Append a value to a list or array.

        If array is not a list, create a new one containing array
        and value.

        """
        if isinstance(array, list):
            array.append(value)
        elif array is None:
            array = value
        elif array != value:
            array = [array, value]
        return array

    @staticmethod
    def parse_versions(versions_list, products):
        """
        Parses the versions, separating by ":" and returning versions
        and products.
        """
        versions = []
        if isinstance(versions_list, list):
            for v in versions_list:
                if v.find(":") > -1:
                    pv = v.split(":")
                    versions = PostgreSQLBase.append_to_var(pv[0], versions)
                    versions = PostgreSQLBase.append_to_var(pv[1], versions)
                else:
                    products = PostgreSQLBase.append_to_var(v, products)
        elif versions_list:
            if versions_list.find(":") > -1:
                pv = versions_list.split(":")
                versions = PostgreSQLBase.append_to_var(pv[0], versions)
                versions = PostgreSQLBase.append_to_var(pv[1], versions)
            else:
                products = PostgreSQLBase.append_to_var(versions_list,
                                                          products)

        return (versions, products)
