import logging
import searchAPI

from datetime import timedelta, datetime

import socorro.lib.util as util
import socorro.lib.datetimeutil as dtutil
import socorro.database.database as db

logger = logging.getLogger("webapi")

class PostgresAPI(searchAPI.SearchAPI):
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
        types -- Types of data to search into. Can be a string or a list of strings.

        Optional arguments:
        for -- Terms to search for. Can be a string or a list of strings.
        product -- Products concerned by this search. Can be a string or a list of strings.
        from -- Only elements after this date. Format must be "YYYY-mm-dd HH:ii:ss.S"
        to -- Only elements before this date. Format must be "YYYY-mm-dd HH:ii:ss.S"
        in -- This is NOT implemented for PostreSQL.
        os -- Limit search to those operating systems. Can be a string or a list of strings. Default to all OS.
        version -- Version of the software. Can be a string or a list of strings. Default to all versions.
        build_id -- Limit search to this particular build of the software. Must be a string. Default to all builds.
        search_mode -- How to search for terms. Must be one of the following: "contains", "is_exactly" or "starts_with". Default to "contains".
        crash_reason --  Restricts search to crashes caused by this reason. Default value is empty.
        """

        # Default dates
        now = datetime.today()
        lastWeek = now - timedelta(7)

        # Getting parameters that have default values
        terms       = kwargs.get("for", "")
        products    = kwargs.get("product", "Firefox")
        from_date   = kwargs.get("from", lastWeek)
        to_date     = kwargs.get("to", now)
        os          = kwargs.get("os", "_all")
        branches    = kwargs.get("branches", None)
        build_id    = kwargs.get("build", None)
        reason      = kwargs.get("crash_reason", None)
        report_type = kwargs.get("report_type", None)
        versionsList = kwargs.get("version", "_all")

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

        # Handling dates
        from_date = self._formatDate(from_date)
        to_date = self._formatDate(to_date)

        # For Postgres, we never search for a list of terms
        if type(terms) is list:
            terms = " ".join(terms)

        # Searching for terms in signature
        isTermsAList = type(terms) is list

        if terms:
            terms = self._prepareTerms(terms, isTermsAList, search_mode)

        # Searching for terms in plugins
        if report_process == "plugin" and plugin_term:
            plugin_term = self._prepareTerms(plugin_term, (type(plugin_term) is list), plugin_search_mode)

        # Parsing the versions
        (versions, products) = self._parseVersions(versionsList, products)

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
        params = self._dispatchParams(params, "term", terms)
        params = self._dispatchParams(params, "product", products)
        params = self._dispatchParams(params, "os", os)
        params = self._dispatchParams(params, "version", versions)
        params = self._dispatchParams(params, "build", build_id)
        params = self._dispatchParams(params, "reason", reason)
        params = self._dispatchParams(params, "plugin_term", plugin_term)
        params = self._dispatchParams(params, "branch", branches)

        # Preparing the different parts of the sql query

        #---------------------------------------------------------------
        # SELECT
        #---------------------------------------------------------------

        sqlSelect = self._generateSqlSelect(report_process)

        # Adding count for each OS
        for i in self.context.platforms:
            params[ "os_" + i["id"] ] = i["name"]

        #---------------------------------------------------------------
        # FROM
        #---------------------------------------------------------------

        sqlFrom = self._generateSqlFrom(report_process, branches)

        #---------------------------------------------------------------
        # WHERE
        #---------------------------------------------------------------

        sqlWhere = ["""
            WHERE r.date_processed BETWEEN %(from_date)s AND %(to_date)s
        """]

        ## Adding terms to where clause
        if terms:
            if not isTermsAList and search_mode == "is_exactly":
                sqlWhere.append("r.signature=%(term)s")
            elif not isTermsAList:
                sqlWhere.append("r.signature LIKE %(term)s")
            else:
                if search_mode == "is_exactly":
                    comp = "="
                else:
                    comp = "LIKE"

                sqlWhere.append( "".join( ( "(", self._arrayToString(xrange(len(terms)), " OR ", "r.signature"+comp+"%(term", ")s"), ")" ) ) )

        ## Adding products to where clause
        if type(products) is list:
            sqlWhere.append( "".join( ( "(", self._arrayToString(xrange(len(products)), " OR ", "r.product=%(product", ")s"), ")" ) ) )
        else:
            sqlWhere.append("r.product=%(product)s" )

        ## Adding OS to where clause
        if os != "_all":
            if type(os) is list:
                sqlWhere.append( "".join( ( "(", self._arrayToString(xrange(len(os)), " OR ", "r.os_name=%(os", ")s"), ")" ) ) )
            else:
                sqlWhere.append("r.os_name=%(os)s")

        ## Adding branches to where clause
        if branches:
            if type(branches) is list:
                sqlWhere.append( "".join( ( "(", self._arrayToString(xrange(len(branches)), " OR ", "branches.branch=%(branch", ")s"), ")" ) ) )
            else:
                sqlWhere.append("branches.branch=%(branch)s")

        ## Adding versions to where clause
        if versions != "_all" and len(versions):
            if type(versions) is list:
                sqlWhere.append( "".join( ( "(", " OR ".join("%s%s%s%s%s" % ("( r.product=%(version", x, ")s AND r.version=%(version", x+1, ")s )") for x in xrange(0, len(versions), 2) ), ")" ) ) )
            else:
                sqlWhere.append("r.version=%(version)s")

        ## Adding build id to where clause
        if build_id:
            if type(build_id) is list:
                sqlWhere.append( "".join( ( "(", self._arrayToString(xrange(len(build_id)), " OR ", "r.build=%(build", ")s"), ")" ) ) )
            else:
                sqlWhere.append("r.build=%(build)s")

        ## Adding reason to where clause
        if reason:
            if type(reason) is list:
                sqlWhere.append( "".join( ( "(", self._arrayToString(xrange(len(reason)), " OR ", "r.reason=%(reason", ")s"), ")" ) ) )
            else:
                sqlWhere.append("r.reason=%(reason)s")

        if report_type == "crash":
            sqlWhere.append("r.hangid IS NULL")
        elif report_type == "hang":
            sqlWhere.append("r.hangid IS NOT NULL")

        ## Searching through plugins
        if report_process == "plugin":
            sqlWhere.append("r.process_type = 'plugin'")
            sqlWhere.append("plugins_reports.date_processed BETWEEN %(from_date)s AND %(to_date)s")

            if plugin_term:
                comp = " LIKE "
                if plugin_search_mode == "contains":
                    plugin_term = "".join( ( "%", plugin_term, "%") )
                elif plugin_search_mode == "starts_with":
                    plugin_term = plugin_term + "%"
                else:
                    comp = "="

                field = "plugins.name"
                if plugin_in == "filename":
                    field = "plugins.filename"

                if type(plugin_term) is list:
                    sqlWhere.append( "".join( ( self._arrayToString(xrange(len(plugin_term)), " OR ", field + comp +"%(plugin_term", ")s"), ")" ) ) )
                else:
                    sqlWhere.append( "".join( ( field, comp, "%(plugin_term)s" ) ) )

        elif report_process == "browser":
            sqlWhere.append("r.process_type IS NULL")

        sqlWhere = " AND ".join(sqlWhere)

        #---------------------------------------------------------------
        # GROUP BY
        #---------------------------------------------------------------

        sqlGroup = self._generateSqlGroup(report_process)

        #---------------------------------------------------------------
        # ORDER BY
        #---------------------------------------------------------------

        sqlOrder = """
            ORDER BY total DESC
        """

        #---------------------------------------------------------------
        # LIMIT OFFSET
        #---------------------------------------------------------------

        sqlLimit = """
            LIMIT %(limit)s
            OFFSET %(offset)s
        """

        # Assembling the query
        sqlQuery = " ".join( ( sqlSelect, sqlFrom, sqlWhere, sqlGroup, sqlOrder, sqlLimit ) )

        # Query for counting the results
        sqlCountQuery = " ".join( ( "SELECT count(DISTINCT r.signature) ", sqlFrom, sqlWhere ) )

        # Creating the connection to the DB
        self.connection = self.database.connection()
        cur = self.connection.cursor()

        # Querying the DB
        try:
            total = db.singleValueSql(cur, sqlCountQuery, params)
        except Exception:
            total = 0
            util.reportExceptionAndContinue(logger)

        # No need to call Postgres if we know there will be no results
        if total != 0:
            try:
                results = db.execute(cur, sqlQuery, params)
            except Exception:
                results = []
                util.reportExceptionAndContinue(logger)
        else:
            results = []

        jsonRes = {
            "total" : total,
            "hits" : []
        }

        # Transforming the results into what we want
        for crash in results:
            row = dict( zip( ("signature", "count", "is_windows", "is_mac", "is_linux", "is_solaris"), crash ) )
            jsonRes["hits"].append(row)

        self.connection.close()

        return jsonRes

    def _dispatchParams(self, params, key, value):
        """
        Dispatch a parameter or a list of parameters into the params array.

        """
        if type(value) is not list:
            params[key] = value
        else:
            for i in xrange(len(value)):
                params[key+str(i)] = value[i]
        return params

    def _appendToVar(self, value, array):
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

    def _parseVersions(self, versionsList, products):
        """
        Parses the versions, separating by ":" and returning versions
        and products.

        """
        versions = []
        if type(versionsList) is list:
            for v in versionsList:
                if v.find(":") > -1:
                    pv = v.split(":")
                    versions = self._appendToVar(pv[0], versions)
                    versions = self._appendToVar(pv[1], versions)
                else:
                    products = self._appendToVar(v, products)
        elif versionsList != "_all":
            if versionsList.find(":") > -1:
                pv = versionsList.split(":")
                versions = self._appendToVar(pv[0], versions)
                versions = self._appendToVar(pv[1], versions)
            else:
                products = self._appendToVar(versionsList, products)

        return (versions, products)

    def _prepareTerms(self, terms, isTermsAList, search_mode):
        """
        Prepare terms for search, adding '%' where needed,
        given the search mode.

        """
        if search_mode == "contains" and isTermsAList:
            for i in xrange(len(terms)):
                terms[i] = "%" + terms[i] + "%"
        elif search_mode == "contains":
            terms = "%" + terms + "%"
        elif search_mode == "starts_with" and isTermsAList:
            for i in xrange(len(terms)):
                terms[i] = terms[i] + "%"
        elif search_mode == "starts_with":
            terms = terms + "%"
        return terms

    def _generateSqlSelect(self, report_process):
        """
        Generates and returns the SELECT part of the final SQL query.

        """
        sqlSelect = ["SELECT r.signature, count(r.id) as total"]

        ## Adding count for each OS
        for i in self.context.platforms:
            sqlSelect.append( "".join( ( "count(CASE WHEN (r.os_name = %(os_", i["id"], ")s) THEN 1 END) AS is_", i["id"] ) ) )

        ## Searching through plugins
        if report_process == "plugin":
            sqlSelect.append("plugins.name AS pluginName, plugins_reports.version AS pluginVersion, plugins.filename AS pluginFilename")

        return ", ".join(sqlSelect)

    def _generateSqlFrom(self, report_process, branches):
        """
        Generates and returns the FROM part of the final SQL query.

        """
        sqlFrom = ["FROM reports r"]

        ## Searching through plugins
        if report_process == "plugin":
            sqlFrom.append("plugins_reports ON plugins_reports.report_id = r.id")
            sqlFrom.append("plugins ON plugins_reports.plugin_id = plugins.id")

        ## Searching through branches
        if branches:
            sqlFrom.append("branches ON (branches.product = r.product AND branches.version = r.version)")

        return " JOIN ".join(sqlFrom)

    def _generateSqlGroup(self, report_process):
        """
        Generates and returns the GROUP BY part of the final SQL query.

        """
        sqlGroup = ["GROUP BY r.signature"]

        # Searching through plugins
        if report_process == "plugin":
            sqlGroup.append("pluginName, pluginVersion, pluginFilename ")

        return ", ".join(sqlGroup)
