import logging

from datetime import timedelta, datetime

import socorro.lib.util as util
import socorro.lib.datetimeutil as dtutil
import socorro.database.database as db
import searchapi as sapi

logger = logging.getLogger("webapi")

class PostgresAPI(sapi.SearchAPI):
    """
    Implements the search API using PostgreSQL.
    See https://wiki.mozilla.org/Socorro/ElasticSearch_API

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

    def query(self, types, sql_query):
        """
        This method is not implemented for PostgreSQL.
        See https://wiki.mozilla.org/Socorro/ElasticSearch_API#Query

        """
        raise NotImplementedError("Method query() is not implemented for PostgreSQL. ")

    def search(self, types, **kwargs):
        """
        Search for crashes and return them.
        See https://wiki.mozilla.org/Socorro/ElasticSearch_API#Search

        Keyword arguments:
        types -- Type of data to return. Only "signatures" is supported for postgres.

        Optional arguments: see SearchAPI.get_parameters
        """

        # Default dates
        now = datetime.today()
        lastweek = now - timedelta(7)

        # Getting parameters that have default values
        terms       = kwargs.get("for", "")
        products    = kwargs.get("product", "Firefox")
        from_date   = kwargs.get("from", lastweek)
        to_date     = kwargs.get("to", now)
        os          = kwargs.get("os", "_all")
        branches    = kwargs.get("branches", None)
        build_id    = kwargs.get("build", None)
        reason      = kwargs.get("crash_reason", None)
        report_type = kwargs.get("report_type", None)
        versions_list = kwargs.get("version", "_all")

        report_process      = kwargs.get("report_process", None)
        plugin_in           = kwargs.get("plugin_in", None)
        plugin_search_mode  = kwargs.get("plugin_search_mode", None)
        plugin_term         = kwargs.get("plugin_term", "")

        search_mode     = kwargs.get("search_mode", "starts_with")
        result_number   = kwargs.get("result_number", 100)
        result_offset   = kwargs.get("result_offset", 0)

        # Default mode falls back to starts_with for postgres
        if search_mode == "default":
            search_mode = "starts_with"
        if plugin_search_mode == "default":
            plugin_search_mode = "starts_with"

        # Handling dates
        from_date = PostgresAPI.format_date(from_date)
        to_date = PostgresAPI.format_date(to_date)

        # For Postgres, we never search for a list of terms
        if type(terms) is list:
            terms = " ".join(terms)

        # For Postgres, we never search for a list of terms
        if type(terms) is list:
            terms = " ".join(terms)

        # Searching for terms in signature
        is_terms_a_list = type(terms) is list

        if terms:
            terms = PostgresAPI.prepare_terms(terms, is_terms_a_list, search_mode)

        # Searching for terms in plugins
        if report_process == "plugin" and plugin_term:
            plugin_term = PostgresAPI.prepare_terms(plugin_term, (type(plugin_term) is list), plugin_search_mode)

        # Parsing the versions
        (versions, products) = PostgresAPI.parse_versions(versions_list, products)

        # Changing the OS ids to OS names
        if type(os) is list:
            for i in xrange(len(os)):
                for platform in self.context.platforms:
                    if platform["id"] == os[i]:
                        os[i] = platform["name"]
        else:
            for platform in self.context.platforms:
                if platform["id"] == os:
                    os = platform["name"]

        # Changing the OS ids to OS names
        if type(os) is list:
            for i in xrange(len(os)):
                for platform in self.context.platforms:
                    if platform["id"] == os[i]:
                        os[i] = platform["name"]
        else:
            for platform in self.context.platforms:
                if platform["id"] == os:
                    os = platform["name"]

        # Creating the parameters for the sql query
        params = {
            "from_date" : from_date,
            "to_date" : to_date,
            "limit" : int(result_number),
            "offset" : int(result_offset)
        }
        params = PostgresAPI.dispatch_params(params, "term", terms)
        params = PostgresAPI.dispatch_params(params, "product", products)
        params = PostgresAPI.dispatch_params(params, "os", os)
        params = PostgresAPI.dispatch_params(params, "version", versions)
        params = PostgresAPI.dispatch_params(params, "build", build_id)
        params = PostgresAPI.dispatch_params(params, "reason", reason)
        params = PostgresAPI.dispatch_params(params, "plugin_term", plugin_term)
        params = PostgresAPI.dispatch_params(params, "branch", branches)

        # Preparing the different parts of the sql query

        #---------------------------------------------------------------
        # SELECT
        #---------------------------------------------------------------

        sql_select = self.generate_sql_select(report_process)

        # Adding count for each OS
        for i in self.context.platforms:
            params[ "os_" + i["id"] ] = i["name"]

        #---------------------------------------------------------------
        # FROM
        #---------------------------------------------------------------

        sql_from = self.generate_sql_from(report_process, branches)

        #---------------------------------------------------------------
        # WHERE
        #---------------------------------------------------------------

        sql_where = ["""
            WHERE r.date_processed BETWEEN %(from_date)s AND %(to_date)s
        """]

        ## Adding terms to where clause
        if terms:
            if not is_terms_a_list and search_mode == "is_exactly":
                sql_where.append("r.signature=%(term)s")
            elif not is_terms_a_list:
                sql_where.append("r.signature LIKE %(term)s")
            else:
                if search_mode == "is_exactly":
                    comp = "="
                else:
                    comp = "LIKE"

                sql_where.append( "".join( ( "(", PostgresAPI.array_to_string(xrange(len(terms)), " OR ", "r.signature"+comp+"%(term", ")s"), ")" ) ) )

        ## Adding products to where clause
        if type(products) is list:
            sql_where.append( "".join( ( "(", PostgresAPI.array_to_string(xrange(len(products)), " OR ", "r.product=%(product", ")s"), ")" ) ) )
        else:
            sql_where.append("r.product=%(product)s" )

        ## Adding OS to where clause
        if os != "_all":
            if type(os) is list:
                sql_where.append( "".join( ( "(", PostgresAPI.array_to_string(xrange(len(os)), " OR ", "r.os_name=%(os", ")s"), ")" ) ) )
            else:
                sql_where.append("r.os_name=%(os)s")

        ## Adding branches to where clause
        if branches:
            if type(branches) is list:
                sql_where.append( "".join( ( "(", PostgresAPI.array_to_string(xrange(len(branches)), " OR ", "branches.branch=%(branch", ")s"), ")" ) ) )
            else:
                sql_where.append("branches.branch=%(branch)s")

        ## Adding versions to where clause
        if versions != "_all" and len(versions):
            if type(versions) is list:
                sql_where.append( "".join( ( "(", " OR ".join("%s%s%s%s%s" % ("( r.product=%(version", x, ")s AND r.version=%(version", x+1, ")s )") for x in xrange(0, len(versions), 2) ), ")" ) ) )
            else:
                sql_where.append("r.version=%(version)s")

        ## Adding build id to where clause
        if build_id:
            if type(build_id) is list:
                sql_where.append( "".join( ( "(", PostgresAPI.array_to_string(xrange(len(build_id)), " OR ", "r.build=%(build", ")s"), ")" ) ) )
            else:
                sql_where.append("r.build=%(build)s")

        ## Adding reason to where clause
        if reason:
            if type(reason) is list:
                sql_where.append( "".join( ( "(", PostgresAPI.array_to_string(xrange(len(reason)), " OR ", "r.reason=%(reason", ")s"), ")" ) ) )
            else:
                sql_where.append("r.reason=%(reason)s")

        if report_type == "crash":
            sql_where.append("r.hangid IS NULL")
        elif report_type == "hang":
            sql_where.append("r.hangid IS NOT NULL")

        ## Searching through plugins
        if report_process == "plugin":
            sql_where.append("r.process_type = 'plugin'")
            sql_where.append("plugins_reports.date_processed BETWEEN %(from_date)s AND %(to_date)s")

            if plugin_term:
                comp = "="

                if plugin_search_mode == "contains" or plugin_search_mode == "starts_with":
                    comp = " LIKE "

                field = "plugins.name"
                if plugin_in == "filename":
                    field = "plugins.filename"

                if type(plugin_term) is list:
                    sql_where.append( "".join( ( "(", PostgresAPI.array_to_string(xrange(len(plugin_term)), " OR ", field + comp +"%(plugin_term", ")s"), ")" ) ) )
                else:
                    sql_where.append( "".join( ( field, comp, "%(plugin_term)s" ) ) )

        elif report_process == "browser":
            sql_where.append("r.process_type IS NULL")

        sql_where = " AND ".join(sql_where)

        #---------------------------------------------------------------
        # GROUP BY
        #---------------------------------------------------------------

        sql_group = self.generate_sql_group(report_process)

        #---------------------------------------------------------------
        # ORDER BY
        #---------------------------------------------------------------

        sql_order = """
            ORDER BY total DESC
        """

        #---------------------------------------------------------------
        # LIMIT OFFSET
        #---------------------------------------------------------------

        sql_limit = """
            LIMIT %(limit)s
            OFFSET %(offset)s
        """

        # Assembling the query
        sql_query = " ".join( ( "/* socorro.search.postgresAPI search */", sql_select, sql_from, sql_where, sql_group, sql_order, sql_limit ) )

        # Query for counting the results
        sql_count_query = " ".join( ( "/* socorro.search.postgresAPI search.count */ SELECT count(DISTINCT r.signature) ", sql_from, sql_where ) )

        # Creating the connection to the DB
        self.connection = self.database.connection()
        cur = self.connection.cursor()

        # Querying the DB
        try:
            total = db.singleValueSql(cur, sql_count_query, params)
        except Exception:
            total = 0
            util.reportExceptionAndContinue(logger)

        # No need to call Postgres if we know there will be no results
        if total != 0:
            try:
                results = db.execute(cur, sql_query, params)
            except Exception:
                results = []
                util.reportExceptionAndContinue(logger)
        else:
            results = []

        json_result = {
            "total" : total,
            "hits" : []
        }

        # Transforming the results into what we want
        for crash in results:
            if report_process == "plugin":
                row = dict( zip( ("signature", "count", "is_windows", "is_mac", "is_linux", "is_solaris", "numhang", "numplugin", "pluginname", "pluginversion", "pluginfilename"), crash ) )
            else:
                row = dict( zip( ("signature", "count", "is_windows", "is_mac", "is_linux", "is_solaris", "numhang", "numplugin"), crash ) )
            json_result["hits"].append(row)

        self.connection.close()

        return json_result

    def report(self, name, **kwargs):
        """
        Not implemented yet.

        """
        raise NotImplemented

    def generate_sql_select(self, report_process):
        """
        Generates and returns the SELECT part of the final SQL query.

        """
        sql_select = ["SELECT r.signature, count(r.id) as total"]

        ## Adding count for each OS
        for i in self.context.platforms:
            sql_select.append( "".join( ( "count(CASE WHEN (r.os_name = %(os_", i["id"], ")s) THEN 1 END) AS is_", i["id"] ) ) )

        sql_select.append("SUM (CASE WHEN r.hangid IS NULL THEN 0  ELSE 1 END) AS numhang")
        sql_select.append("SUM (CASE WHEN r.process_type IS NULL THEN 0  ELSE 1 END) AS numplugin")

        ## Searching through plugins
        if report_process == "plugin":
            sql_select.append("plugins.name AS pluginName, plugins_reports.version AS pluginVersion, plugins.filename AS pluginFilename")

        return ", ".join(sql_select)

    def generate_sql_from(self, report_process, branches):
        """
        Generates and returns the FROM part of the final SQL query.

        """
        sql_from = ["FROM reports r"]

        ## Searching through plugins
        if report_process == "plugin":
            sql_from.append("plugins_reports ON plugins_reports.report_id = r.id")
            sql_from.append("plugins ON plugins_reports.plugin_id = plugins.id")

        ## Searching through branches
        if branches:
            sql_from.append("branches ON (branches.product = r.product AND branches.version = r.version)")

        return " JOIN ".join(sql_from)

    def generate_sql_group(self, report_process):
        """
        Generates and returns the GROUP BY part of the final SQL query.

        """
        sql_group = ["GROUP BY r.signature"]

        # Searching through plugins
        if report_process == "plugin":
            sql_group.append("pluginName, pluginVersion, pluginFilename ")

        return ", ".join(sql_group)

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
