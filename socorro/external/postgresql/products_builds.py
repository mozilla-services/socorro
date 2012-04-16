import logging
import web

from datetime import timedelta
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib.datetimeutil import utc_now

import socorro.database.database as db
import socorro.lib.external_common as external_common
import socorro.lib.util as util

logger = logging.getLogger("webapi")


class MissingOrBadArgumentException(Exception):
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
        except MissingOrBadArgumentException:
            raise web.webapi.BadRequest()
        except Exception:
            util.reportExceptionAndContinue(logger)
            raise web.webapi.InternalError()

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

        if "product" not in params or not params["product"]:
            raise MissingOrBadArgumentException(
                        "Mandatory parameter 'product' is missing or empty")

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
