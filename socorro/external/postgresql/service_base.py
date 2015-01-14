# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import psycopg2

from configman import Namespace, class_converter

from .dbapi2_util import (
    execute_query_fetchall,
    execute_no_results,
    single_value_sql,
)
from socorro.external import DatabaseError
from socorro.webapi.webapiService import DataserviceWebServiceBase


#==============================================================================
class PostgreSQLWebServiceBase(DataserviceWebServiceBase):

    """
    Base class for PostgreSQL based service implementations.
    """

    required_config = Namespace()
    required_config.add_option(
        'crashstorage_class',
        doc='the source storage class',
        default='socorro'
            '.external.postgresql.crashstorage.PostgreSQLCrashStorage',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'output_is_json',
        doc='Does this service provide json output?',
        default=True,
    )
    required_config.add_option(
        'cache_seconds',
        doc='number of seconds to store results in filesystem cache',
        default=3600,
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        """
        Store the config and create a connection to the database.

        Keyword arguments:
        config -- Configuration of the application.

        """
        super(PostgreSQLWebServiceBase, self).__init__(config)
        self.crash_store = self.config.crashstorage_class(self.config)
        self.database = self.crash_store.database
        self.transaction = self.crash_store.transaction

    #--------------------------------------------------------------------------
    @contextlib.contextmanager
    def get_connection(self):
        with self.database() as connection:
            yield connection

    #--------------------------------------------------------------------------
    def query(
        self,
        sql,
        params=None,
        error_message=None,
        action=execute_query_fetchall
    ):
        """Return the result of a query executed against PostgreSQL.

        Create a connection, open a cursor, execute the query and return the
        results. If an error occures, log it and raise a DatabaseError.

        Keyword arguments:
        sql -- SQL query to execute.
        params -- Parameters to merge into the SQL query when executed.
        error_message -- Eventual error message to log.

        """
        try:
            result = self.transaction(
                action,
                sql,
                params
            )
            return result
        except psycopg2.Error, x:
            raise
            self.config.logger.error(
                error_message if error_message else str(x),
                exc_info=True
            )
            raise DatabaseError(error_message)

    #--------------------------------------------------------------------------
    def execute_no_results(self, sql, params=None, error_message=None):
        """Return the result of a delete or update SQL query

        Keyword arguments:
        sql -- SQL query to execute.
        params -- Parameters to merge into the SQL query when executed.
        error_message -- Eventual error message to log.

        """
        return self.query(
            sql,
            params=params,
            error_message=error_message,
            action=execute_no_results
        )

    #--------------------------------------------------------------------------
    def count(self, sql, params=None, error_message=None):
        """Return the result of a count SQL query executed against PostgreSQL.

        Create a connection, open a cursor, execute the query and return the
        result. If an error occures, log it and raise a DatabaseError.

        Keyword arguments:
        sql -- SQL query to execute.
        params -- Parameters to merge into the SQL query when executed.
        error_message -- Eventual error message to log.

        """
        return self.query(
            sql,
            params=params,
            error_message=error_message,
            action=single_value_sql
        )

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
    @staticmethod
    def prepare_terms(terms, search_mode):
        """
        Prepare terms for search, adding '%' where needed,
        given the search mode.
        """
        if search_mode in ("contains", "starts_with"):
            terms = terms.replace("_", "\_").replace("%", "\%")

        if search_mode == "contains":
            terms = "%" + terms + "%"
        elif search_mode == "starts_with":
            terms = terms + "%"
        return terms

    #--------------------------------------------------------------------------
    @staticmethod
    def dispatch_params(sql_params, key, value):
        """
        Dispatch a parameter or a list of parameters into the params array.
        """
        if not isinstance(value, list):
            sql_params[key] = value
        else:
            for i, elem in enumerate(value):
                sql_params[key + str(i)] = elem
        return sql_params
