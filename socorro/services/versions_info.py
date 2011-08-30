import logging

import socorro.lib.util as util
import socorro.database.database as db
import socorro.search.postgresql as pg
import socorro.webapi.webapiService as webapi

logger = logging.getLogger("webapi")


class VersionsInfo(webapi.JsonServiceBase):

    """
    Return information about versions of a product.
    """

    def __init__(self, config):
        """
        Constructor
        """
        super(VersionsInfo, self).__init__(config)
        try:
            self.database = db.Database(config)
        except (AttributeError, KeyError):
            util.reportExceptionAndContinue(logger)
        logger.debug('VersionsInfo __init__')

    uri = '/201105/util/versions_info/(.*)'

    def get(self, *args):
        """
        Called when a get HTTP request is executed to /search
        """
        # Parse parameters
        params = self._parse_query_string(args[0])
        return self.versions_info(params)

    def versions_info(self, params):
        """
        Return information about versions of a product.

        Parameters:
        version - List of products and versions.

        Return:
        None if version is null or empty ;
        Otherwise a dictionary of data about a version, i.e.:
        {
            "product_name:version_string": {
                "version_string": "string",
                "product_name": "string",
                "major_version": "string" or None,
                "release_channel": "string" or None,
                "build_id": [list, of, decimals] or None
            }
        }

        """
        if "version" not in params or not params["version"]:
            return None

        products_list = []
        (versions_list, products_list) = pg.PostgresAPI.parse_versions(
                                                            params["version"],
                                                            products_list)

        if not versions_list:
            return None

        versions = []
        products = []
        for x in xrange(0, len(versions_list), 2):
            products.append(versions_list[x])
            versions.append(versions_list[x + 1])

        params = {}
        params = pg.PostgresAPI.dispatch_params(params, "product", products)
        params = pg.PostgresAPI.dispatch_params(params, "version", versions)

        where = []
        for i in xrange(len(products)):
            index = str(i)
            where.append(index.join(("(pi.product_name = %(product",
                                     ")s AND pi.version_string = %(version",
                                     ")s)")))

        sql = """/* socorro.middleware.postgresql.util.Util.versions_info */
        SELECT pi.version_string, pi.product_name, which_table, major_version,
               pv.build_type, pvb.build_id
        FROM product_info pi
            LEFT JOIN product_versions pv ON
                (pv.product_version_id = pi.product_version_id)
            JOIN product_version_builds pvb ON
                (pv.product_version_id = pvb.product_version_id)
        WHERE %s
        """ % " OR ".join(where)

        # Creating the connection to the DB
        self.connection = self.database.connection()
        cur = self.connection.cursor()

        try:
            results = db.execute(cur, sql, params)
        except Exception:
            results = []
            util.reportExceptionAndContinue(logger)

        res = {}
        for line in results:
            row = dict(zip(("version_string", "product_name", "which_table",
                            "major_version", "release_channel", "build_id"),
                           line))

            key = ":".join((row["product_name"], row["version_string"]))

            if key in res:
                # That key already exists, just add it the new buildid
                res[key]["build_id"].append(int(row["build_id"]))
            else:
                if row["which_table"] == "old":
                    row["release_channel"] = row["build_id"] = None
                del row["which_table"]

                if row["build_id"]:
                    row["build_id"] = [int(row["build_id"])]

                res[key] = row

        return res

    def _parse_query_string(self, query_string):
        """
        Take a string of parameters and return a dictionary of key, value.
        """
        terms_sep = "+"
        params_sep = "/"

        args = query_string.split(params_sep)

        params = {}
        for i in xrange(0, len(args), 2):
            if args[i] and args[i + 1]:
                params[args[i]] = args[i + 1]

        for i in params:
            if params[i].find(terms_sep) > -1:
                params[i] = params[i].split(terms_sep)

        return params
