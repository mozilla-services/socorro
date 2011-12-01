import logging

import socorro.database.database as db
import socorro.lib.util as util

logger = logging.getLogger("webapi")


def add_param_to_dict(dictionary, key, value):
    """
    Dispatch a list of parameters into a dictionary.
    """
    for i, elem in enumerate(value):
        dictionary[key + str(i)] = elem
    return dictionary


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

    @staticmethod
    def build_reports_sql_from(params):
        """
        Generate and return the FROM part of the final SQL query.
        """
        sql_from = ["FROM reports r"]

        ## Searching through plugins
        if params["report_process"] == "plugin":
            sql_from.append(("plugins_reports ON "
                             "plugins_reports.report_id = r.id"))
            sql_from.append(("plugins ON "
                             "plugins_reports.plugin_id = plugins.id"))

        ## Searching through branches
        if params["branches"]:
            sql_from.append(("branches ON (branches.product = r.product "
                             "AND branches.version = r.version)"))

        sql_from = " JOIN ".join(sql_from)
        return sql_from

    @staticmethod
    def build_reports_sql_where(params, sql_params):
        """
        """
        sql_where = ["""
            WHERE r.date_processed BETWEEN %(from_date)s AND %(to_date)s
        """]

        sql_params["from_date"] = params["from_date"]
        sql_params["to_date"] = params["to_date"]

        ## Adding terms to where clause
        if params["terms"]:
            if params["search_mode"] == "is_exactly":
                sql_where.append("r.signature=%(term)s")
            else:
                sql_where.append("r.signature LIKE %(term)s")
            sql_params["term"] = params["terms"]

        ## Adding products to where clause
        if params["products"]:
            products_list = ["r.product=%(product" + str(x) + ")s"
                             for x in range(len(params["products"]))]
            sql_where.append("(%s)" % (" OR ".join(products_list)))
            sql_params = add_param_to_dict(sql_params, "product",
                                           params["products"])

        ## Adding OS to where clause
        if params["os"]:
            os_list = ["r.os_name=%(os" + str(x) + ")s"
                       for x in range(len(params["os"]))]
            sql_where.append("(%s)" % (" OR ".join(os_list)))
            sql_params = add_param_to_dict(sql_params, "os", params["os"])

        ## Adding branches to where clause
        if params["branches"]:
            branches_list = ["branches.branch=%(branch" + str(x) + ")s"
                             for x in range(len(params["branches"]))]
            sql_where.append("(%s)" % (" OR ".join(branches_list)))
            sql_params = add_param_to_dict(sql_params, "branch",
                                           params["branches"])

        ## Adding versions to where clause
        if params["versions"]:
            sql_params = add_param_to_dict(sql_params, "version",
                                           params["versions"])
            versions_info = params["versions_info"]

            versions_where = []

            for x in range(0, len(params["versions"]), 2):
                version_where = []
                version_where.append(str(x).join(("r.product=%(version",
                                                  ")s")))

                key = "%s:%s" % (params["versions"][x],
                                 params["versions"][x + 1])
                version_where = PostgreSQLBase.build_reports_sql_version_where(
                                        key, params["versions"],
                                        versions_info, x, sql_params,
                                        version_where)

                version_where.append(str(x + 1).join((
                                        "r.version=%(version", ")s")))
                versions_where.append("(%s)" % " AND ".join(version_where))

            sql_where.append("(%s)" % " OR ".join(versions_where))

        ## Adding build id to where clause
        if params["build_ids"]:
            build_ids_list = ["r.build=%(build" + str(x) + ")s"
                              for x in range(len(params["build_ids"]))]
            sql_where.append("(%s)" % (" OR ".join(build_ids_list)))
            sql_params = add_param_to_dict(sql_params, "build",
                                           params["build_ids"])

        ## Adding reason to where clause
        if params["reasons"]:
            reasons_list = ["r.reason=%(reason" + str(x) + ")s"
                            for x in range(len(params["reasons"]))]
            sql_where.append("(%s)" % (" OR ".join(reasons_list)))
            sql_params = add_param_to_dict(sql_params, "reason",
                                           params["reasons"])

        ## Adding report type to where clause
        if params["report_type"] == "crash":
            sql_where.append("r.hangid IS NULL")
        elif params["report_type"] == "hang":
            sql_where.append("r.hangid IS NOT NULL")

        ## Searching through plugins
        if params["report_process"] == "plugin":
            sql_where.append("r.process_type = 'plugin'")
            sql_where.append(("plugins_reports.date_processed BETWEEN "
                              "%(from_date)s AND %(to_date)s"))

            if params["plugin_terms"]:
                comp = "="

                if params["plugin_search_mode"] in ("contains", "starts_with"):
                    comp = " LIKE "

                sql_where_plugin_in = []
                for f in params["plugin_in"]:
                    if f == "name":
                        field = "plugins.name"
                    elif f == "filename":
                        field = "plugins.filename"

                    sql_where_plugin_in.append(comp.join((field,
                                                          "%(plugin_term)s")))
                sql_params["plugin_term"] = params["plugin_terms"]

                sql_where.append("(%s)" % " OR ".join(sql_where_plugin_in))

        elif params["report_process"] == "browser":
            sql_where.append("r.process_type IS NULL")

        elif params["report_process"] == "content":
            sql_where.append("r.process_type = 'content'")

        sql_where = " AND ".join(sql_where)
        return (sql_where, sql_params)

    @staticmethod
    def build_reports_sql_limit(params, sql_params):
        """
        """
        sql_limit = """
            LIMIT %(limit)s
            OFFSET %(offset)s
        """
        sql_params["limit"] = params["result_number"]
        sql_params["offset"] = params["result_offset"]

        return (sql_limit, sql_params)

    @staticmethod
    def build_reports_sql_version_where(key, versions, versions_info, x,
                                        sql_params, version_where):
        """
        Return a list of strings for version restrictions.
        """
        if key in versions_info:
            version_info = versions_info[key]
        else:
            version_info = None

        if x is None:
            version_param = "version"
        else:
            version_param = "version%s" % (x + 1)

        if version_info and version_info["release_channel"]:
            if version_info["release_channel"] in ("Beta", "Aurora",
                                                   "Nightly"):
                # Use major_version instead of full version
                sql_params[version_param] = version_info["major_version"]
                # Restrict by release_channel
                version_where.append("r.release_channel ILIKE '%s'" % (
                                            version_info["release_channel"]))
                if version_info["release_channel"] == "Beta":
                    # Restrict to a list of build_id
                    version_where.append("r.build IN ('%s')" % (
                        "', '".join([
                            str(bid) for bid in version_info["build_id"]])))

            else:
                # it's a release
                version_where.append(("r.release_channel NOT IN ('nightly', "
                                      "'aurora', 'beta')"))

        return version_where
