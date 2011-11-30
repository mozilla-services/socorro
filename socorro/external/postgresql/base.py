import logging

import socorro.database.database as db
import socorro.lib.util as util

logger = logging.getLogger("webapi")


class PostgreSQLBase(object):

    """
    Base class for PostgreSQL based service implementations.
    """

    def __init__(self, *args, **kwargs):
        """
        Store the config and create a connection to the database.

        Keyword arguments:
        config -- Configuration of the application.

        """
        self.context = kwargs.get("config")
        try:
            self.database = db.Database(self.context)
        except (AttributeError, KeyError):
            util.reportExceptionAndContinue(logger)

        self.connection = None

    @staticmethod
    def parse_versions(versions_list, products):
        """
        Parses the versions, separating by ":" and returning versions
        and products.
        """
        versions = []

        for v in versions_list:
            if v.find(":") > -1:
                pv = v.split(":")
                versions.append(pv[0])
                versions.append(pv[1])
            else:
                products.append(v)

        return (versions, products)
