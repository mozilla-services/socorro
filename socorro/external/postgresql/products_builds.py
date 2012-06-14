# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import psycopg2
import web

from datetime import timedelta
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib.datetimeutil import utc_now

import socorro.database.database as db
import socorro.lib.buildutil as buildutil
import socorro.lib.external_common as external_common
import socorro.lib.util as util

logger = logging.getLogger("webapi")


class MissingOrBadArgumentError(Exception):
    pass


class ProductsBuilds(PostgreSQLBase):

    """
    Implement the /products/builds service with PostgreSQL.
    """

    def __init__(self, *args, **kwargs):
        super(ProductsBuilds, self).__init__(*args, **kwargs)

    def get(self, **kwargs):
        """
        Return the result of the GET HTTP method applied to products/builds/.

        Return the result of builds(), but raise web-specific exceptions.
        Accept the same parameters than builds().

        """
        try:
            return self.builds(**kwargs)
        except MissingOrBadArgumentError as e:
            raise web.webapi.BadRequest(e)
        except Exception:
            util.reportExceptionAndContinue(logger)
            raise web.webapi.InternalError()

    def _require_parameters(self, params, *required):
        """
        Checks that all required parameters are present in and non-empty in
        params, where required is a list of strings.

        Raises MissingOrBadArgumentError if a required parameter is
        missing or empty.
        """
        for p in required:
            if not params.get(p, None):
                raise MissingOrBadArgumentError(
                    "Mandatory parameter '%s' is missing or empty" % p)

    def builds(self, **kwargs):
        """
        Return information about nightly builds of one or several products.

        See http://socorro.readthedocs.org/en/latest/middleware.html#builds

        Keyword arguments:
        product - Concerned product
        version - Concerned version
        from_date - Retrieve builds from this date to now

        Return:
        [
            {
                "product": "string",
                "version": "string",
                "platform": "string",
                "buildid": "integer",
                "build_type": "string",
                "beta_number": "string",
                "repository": "string",
                "date": "string"
            },
            ...
        ]

        """
        # Default value for from_date
        lastweek = utc_now() - timedelta(7)

        # Parse arguments
        filters = [
            ("product", None, "str"),
            ("version", None, "str"),
            ("from_date", lastweek, "datetime"),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        self._require_parameters(params, "product")

        # FIXME this will be moved to the DB in 7, see bug 740829
        if params["product"].startswith("Fennec"):
            params["release_name"] = "mobile"
        else:
            params["release_name"] = params["product"]

        params["from_date"] = params["from_date"].date()

        sql = ["""/* socorro.external.postgresql.builds.Builds.builds */
            SELECT  version,
                    platform,
                    build_id as buildid,
                    build_type,
                    beta_number,
                    repository,
                    build_date(build_id) as date
            FROM releases_raw
            WHERE product_name = %(release_name)s
            """]

        if params["version"]:
            sql.append("AND version = %(version)s")

        sql.append("""
            AND build_date(build_id) >=
                timestamp with time zone %(from_date)s
            AND repository IN ('mozilla-central', 'mozilla-1.9.2',
                               'comm-central', 'comm-1.9.2',
                               'comm-central-trunk', 'mozilla-central-android')
            ORDER BY build_date(build_id) DESC, product_name ASC, version ASC,
                     platform ASC
        """)

        sql_query = " ".join(sql)

        # Creating the connection to the DB
        self.connection = self.database.connection()
        cur = self.connection.cursor()

        try:
            logger.debug(cur.mogrify(sql_query, params))
            sql_results = db.execute(cur, sql_query, params)
        except Exception:
            sql_results = []
            util.reportExceptionAndContinue(logger)

        results = [dict(zip(("version", "platform", "buildid", "build_type",
                             "beta_number", "repository", "date"),
                            line)) for line in sql_results]

        for i, line in enumerate(results):
            results[i]["product"] = params["product"]
            results[i]["buildid"] = int(line["buildid"])
            results[i]["date"] = line["date"].strftime("%Y-%m-%d")

        return results

    def create(self, **kwargs):
        """
        Create a new build for a product.

        See http://socorro.readthedocs.org/en/latest/middleware.html#builds

        Required keyword arguments:
        product - Concerned product, e.g. firefox
        version - Concerned version, e.g. 9.0a1
        platform - Platform for this build, e.g. win32
        build_id - Build ID for this build (yyyymmdd######)
        build_type - Type of build, e.g. Nightly, Beta, Aurora, Release

        Required if build_type is Beta:
        beta_number - The beta number, e.g. 9.0b#

        Optional keyword arguments:
        repository - Repository this build came from

        Return: (product_name, version)
        """

        # Parse arguments
        filters = [
            ("product", None, "str"),
            ("version", None, "str"),
            ("platform", None, "str"),
            ("build_id", None, "str"),
            ("build_type", None, "str"),
            ("beta_number", None, "str"),
            ("repository", "", "str")
        ]
        params = external_common.parse_arguments(filters, kwargs)

        self._require_parameters(params, "product", "version", "platform",
                                     "build_id", "build_type")

        if params["build_type"].lower() == "beta":
            self._require_parameters(params, "beta_number")

        try:
            connection = self.database.connection()
            cursor = connection.cursor()

            buildutil.insert_build(cursor, params["product"],
                                   params["version"], params["platform"],
                                   params["build_id"], params["build_type"],
                                   params["beta_number"],
                                   params["repository"])
        except psycopg2.Error:
            logger.error("Failed inserting build data into PostgresSQL",
                         exc_info=True)
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

        return (params["product"], params["version"])
