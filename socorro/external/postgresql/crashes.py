# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging
import psycopg2

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external.postgresql.util import Util
from socorro.lib import datetimeutil, external_common, search_common, util

import socorro.database.database as db

logger = logging.getLogger("webapi")


class MissingOrBadArgumentException(Exception):
    pass


class Crashes(PostgreSQLBase):
    """Handle retrieval and creation of crash reports data with PostgreSQL.
    """

    def prepare_search_params(self, **kwargs):
        """Return a dictionary of parameters for a search-like SQL query.

        Uses socorro.lib.search_common.get_parameters() for arguments
        filtering.
        """
        params = search_common.get_parameters(kwargs)

        if not params["signature"]:
            raise MissingOrBadArgumentException(
                        "Mandatory parameter 'signature' is missing or empty")

        params["terms"] = params["signature"]
        params["search_mode"] = "is_exactly"

        # Default mode falls back to starts_with for postgres
        if params["plugin_search_mode"] == "default":
            params["plugin_search_mode"] = "starts_with"

        # Searching for terms in plugins
        if params["report_process"] == "plugin" and params["plugin_terms"]:
            params["plugin_terms"] = " ".join(params["plugin_terms"])
            params["plugin_terms"] = Crashes.prepare_terms(
                                                params["plugin_terms"],
                                                params["plugin_search_mode"])

        # Get information about the versions
        util_service = Util(config=self.context)
        params["versions_info"] = util_service.versions_info(**params)

        # Parsing the versions
        params["versions_string"] = params["versions"]
        (params["versions"], params["products"]) = Crashes.parse_versions(
                                                            params["versions"],
                                                            params["products"])

        # Changing the OS ids to OS names
        for i, elem in enumerate(params["os"]):
            for platform in self.context.platforms:
                if platform["id"] == elem:
                    params["os"][i] = platform["name"]

        return params

    def get_comments(self, **kwargs):
        """Return a list of comments on crash reports, filtered by
        signatures and other fields.

        See socorro.lib.search_common.get_parameters() for all filters.
        """
        # Creating the connection to the DB
        self.connection = self.database.connection()
        cur = self.connection.cursor()

        params = self.prepare_search_params(**kwargs)

        # Creating the parameters for the sql query
        sql_params = {}

        # Preparing the different parts of the sql query

        # WARNING: sensitive data is returned here (email). When there is
        # an authentication mecanism, a verification should be done here.
        sql_select = """
            SELECT
                r.date_processed,
                r.user_comments,
                r.uuid,
                CASE
                    WHEN r.email = '' THEN null
                    WHEN r.email IS NULL THEN null
                    ELSE r.email
                END
        """

        sql_from = self.build_reports_sql_from(params)

        (sql_where, sql_params) = self.build_reports_sql_where(params,
                                                               sql_params,
                                                               self.context)
        sql_where = "%s AND r.user_comments IS NOT NULL" % sql_where

        sql_order = "ORDER BY email ASC, r.date_processed ASC"

        # Assembling the query
        sql_query = " ".join((
                "/* external.postgresql.crashes.Crashes.get_comments */",
                sql_select, sql_from, sql_where, sql_order))

        # Query for counting the results
        sql_count_query = " ".join((
                "/* external.postgresql.crashes.Crashes.get_comments */",
                "SELECT count(*)", sql_from, sql_where))

        # Querying the DB
        try:
            total = db.singleValueSql(cur, sql_count_query, sql_params)
        except db.SQLDidNotReturnSingleValue:
            total = 0
            util.reportExceptionAndContinue(logger)

        results = []

        # No need to call Postgres if we know there will be no results
        if total != 0:
            try:
                results = db.execute(cur, sql_query, sql_params)
            except psycopg2.Error:
                util.reportExceptionAndContinue(logger)

        result = {
            "total": total,
            "hits": []
        }

        # Transforming the results into what we want
        for crash in results:
            row = dict(zip((
                       "date_processed",
                       "user_comments",
                       "uuid",
                       "email"), crash))
            for i in row:
                if isinstance(row[i], datetime.datetime):
                    row[i] = str(row[i])
            result["hits"].append(row)

        self.connection.close()

        return result

    def get_frequency(self, **kwargs):
        """Return the number and frequency of crashes on each OS.

        See socorro.lib.search_common.get_parameters() for all filters.
        """
        params = self.prepare_search_params(**kwargs)

        # Creating the parameters for the sql query
        sql_params = {
            "signature": params.signature
        }

        # Preparing the different parts of the sql query
        sql_select = ["""
            SELECT
                r.build AS build_date,
                COUNT(CASE WHEN (r.signature = %(signature)s) THEN 1 END)
                    AS count,
                CAST(COUNT(CASE WHEN (r.signature = %(signature)s) THEN 1 END)
                    AS FLOAT(10)) / count(r.id) AS frequency,
                COUNT(r.id) AS total
        """]

        ## Adding count for each OS
        for i in self.context.platforms:
            sql_select.append("""
                COUNT(CASE WHEN (r.signature = %%(signature)s
                      AND r.os_name = '%s') THEN 1 END) AS count_%s
            """ % (i["name"], i["id"]))
            sql_select.append("""
                CASE WHEN (COUNT(CASE WHEN (r.os_name = '%s') THEN 1 END)
                > 0) THEN (CAST(COUNT(CASE WHEN (r.signature = '%s'
                AND r.os_name = '%s') THEN 1 END) AS FLOAT(10)) /
                COUNT(CASE WHEN (r.os_name = '%s') THEN 1 END)) ELSE 0.0
                END AS frequency_%s
            """ % (i["name"], params.signature, i["name"], i["name"], i["id"]))

        sql_select = ", ".join(sql_select)

        sql_from = self.build_reports_sql_from(params)

        (sql_where, sql_params) = self.build_reports_sql_where(params,
                                                               sql_params,
                                                               self.context)

        sql_group = "GROUP BY r.build"
        sql_order = "ORDER BY r.build DESC"

        # Assembling the query
        sql = " ".join((
                "/* external.postgresql.crashes.Crashes.get_fequency */",
                sql_select, sql_from, sql_where, sql_group, sql_order))
        sql = str(" ".join(sql.split())) #  better formatting of the sql string

        result = {
            "total": 0,
            "hits": []
        }

        connection = None
        try:
            connection = self.database.connection()
            cur = connection.cursor()
            logger.debug(cur.mogrify(sql, sql_params))
            results = db.execute(cur, sql, sql_params)
        except psycopg2.Error:
            logger.error("Failed retrieving extensions data from PostgreSQL",
                         exc_info=True)
        else:
            fields = ["build_date", "count", "frequency", "total"]
            for i in self.context.platforms:
                fields.append("count_%s" % i["id"])
                fields.append("frequency_%s" % i["id"])

            for crash in results:
                row = dict(zip(fields, crash))
                result["hits"].append(row)
            result["total"] = len(result["hits"])
        finally:
            if connection:
                connection.close()

        return result

    def get_paireduuid(self, **kwargs):
        """Return paired uuid given a uuid and an optional hangid.

        If a hangid is passed, then return only one result. Otherwise, return
        all found paired uuids.

        """
        filters = [
            ("uuid", None, "str"),
            ("hangid", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if not params.uuid:
            raise MissingOrBadArgumentException(
                        "Mandatory parameter 'uuid' is missing or empty")

        crash_date = datetimeutil.uuid_to_date(params.uuid)

        sql = """
            /* socorro.external.postgresql.crashes.Crashes.get_paireduuid */
            SELECT uuid
            FROM reports r
            WHERE r.uuid != %(uuid)s
            AND r.date_processed BETWEEN
                TIMESTAMP %(crash_date)s - CAST('1 day' AS INTERVAL) AND
                TIMESTAMP %(crash_date)s + CAST('1 day' AS INTERVAL)
        """
        sql_params = {
            "uuid": params.uuid,
            "crash_date": crash_date
        }

        if params.hangid is not None:
            sql = """%s
                AND r.hangid = %%(hangid)s
                LIMIT 1
            """ % sql
            sql_params["hangid"] = params.hangid
        else:
            sql = """%s
                AND r.hangid IN (
                    SELECT hangid
                    FROM reports r2
                    WHERE r2.date_processed BETWEEN
                        TIMESTAMP %%(crash_date)s - CAST('1 day' AS INTERVAL)
                        AND
                        TIMESTAMP %%(crash_date)s + CAST('1 day' AS INTERVAL)
                    AND r2.uuid = %%(uuid)s
                )
            """ % sql

        result = {
            "total": 0,
            "hits": []
        }

        try:
            connection = self.database.connection()
            cur = connection.cursor()
            results = db.execute(cur, sql, sql_params)

            # Transforming the results into what we want
            for report in results:
                row = dict(zip(("uuid",), report))
                result["hits"].append(row)
            result["total"] = len(result["hits"])

        except psycopg2.Error:
            logger.error("Failed to retrieve paired uuids from database",
                         exc_info=True)
        finally:
            connection.close()

        return result
