import logging

from datetime import timedelta, datetime

import socorro.database.database as db
import socorro.external.common as co
import socorro.lib.util as util

logger = logging.getLogger("webapi")


class PostgresAPI(co.Common):
    """
    Base class for PostgreSQL based service implementations.

    See https://wiki.mozilla.org/Socorro/Middleware

    """

    def __init__(self, config):
        """
        Default constructor

        """
        super(PostgresAPI, self).__init__(config)
        try:
            self.database = db.Database(config)
        except (AttributeError, KeyError):
            util.reportExceptionAndContinue(logger)

        self.connection = None

    @staticmethod
    def dispatch_params(params, key, value):
        """
        Dispatch a parameter or a list of parameters into the params array.

        """
        if type(value) is not list:
            params[key] = value
        else:
            for i in xrange(len(value)):
                params[key+str(i)] = value[i]
        return params

    @staticmethod
    def append_to_var(value, array):
        """
        Append a value to a list or array.
        If array is not a list, create a new one containing array
        and value.

        """
        if type(array) is list:
            array.append(value)
        elif array == "_all" or array == None:
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
        if type(versions_list) is list:
            for v in versions_list:
                if v.find(":") > -1:
                    pv = v.split(":")
                    versions = PostgresAPI.append_to_var(pv[0], versions)
                    versions = PostgresAPI.append_to_var(pv[1], versions)
                else:
                    products = PostgresAPI.append_to_var(v, products)
        elif versions_list != "_all":
            if versions_list.find(":") > -1:
                pv = versions_list.split(":")
                versions = PostgresAPI.append_to_var(pv[0], versions)
                versions = PostgresAPI.append_to_var(pv[1], versions)
            else:
                products = PostgresAPI.append_to_var(versions_list, products)

        return (versions, products)

    @staticmethod
    def prepare_terms(terms, is_terms_a_list, search_mode):
        """
        Prepare terms for search, adding '%' where needed,
        given the search mode.

        """
        if search_mode == "contains" and is_terms_a_list:
            for i in xrange(len(terms)):
                terms[i] = "%" + terms[i] + "%"
        elif search_mode == "contains":
            terms = "%" + terms + "%"
        elif search_mode == "starts_with" and is_terms_a_list:
            for i in xrange(len(terms)):
                terms[i] = terms[i] + "%"
        elif search_mode == "starts_with":
            terms = terms + "%"
        return terms
