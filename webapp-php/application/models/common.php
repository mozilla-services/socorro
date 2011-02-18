<?php defined('SYSPATH') or die('No direct script access.');

require_once(Kohana::find_file('libraries', 'crash', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'moz_pager', TRUE, 'php'));

/**
 * Common DB queries that span multiple tables and perform aggregate calculations or statistics.
 */
class Common_Model extends Model {

    /**
     * Perform overall initialization for the model.
     */
    public function __construct() {
        parent::__construct();

        $this->branch_model   = new Branch_Model();
        $this->platform_model = new Platform_Model();
    }

   /**
     * Fetch all of the comments associated with a particular Crash Signature.
     *
     * @access 	public
     * @param   string A Crash Signature
     * @return  array 	An array of comments
     * @see getCommentsBySignature
     */
    public function getCommentsBySignature($signature) {
        $params = array('signature' => $signature, 
			'range_value' => 2, 'range_unit' => 'weeks',
			'product' => NULL,  'version' => NULL, 
			'branch' => NULL,   'platform' => NULL,
			'query' => NULL, 'date' => NULL);
	return $this->getCommentsByParams($params);
    }
    
    /**
     * Fetch all of the comments associated with a particular Crash Signature.
     * 
     * @access 	public
     * @param	array 	An array of parameters
     * @return  array 	An array of comments
     */
    public function getCommentsByParams($params) {
        list($from_tables, $join_tables, $where) = $this->_buildCriteriaFromSearchParams($params);

        $sql =
	    "/* soc.web report.getCommentsBySignature */ " .
            " SELECT 
				reports.client_crash_date, 
				reports.user_comments, 
                                reports.uuid, 
				CASE 
					WHEN reports.email = '' THEN null
					WHEN reports.email IS NULL THEN null
					ELSE reports.email
					END " .
            " FROM  " . join(', ', $from_tables);
        if(count($join_tables) > 0) {
	    $sql .= " JOIN  " . join("\nJOIN ", $join_tables);
        }

        $sql .= " WHERE reports.user_comments IS NOT NULL " . 
	        " AND " . join(' AND ', $where) .
	        " ORDER BY email ASC, reports.client_crash_date ASC ";
	return $this->fetchRows($sql);
    }

    /**
     * Find top report signatures for the given search parameters.
     *
     * @param  array  An array of parameters
     * @param  string The type of query to perform. Options: 'results', 'count'
     * @param  int  The number of results to pull for this query
     * @param  int  The offset for this query
     * @return array|int Return an array of results of return_type = 'results', integer if 'counts'
     */
    public function queryTopSignatures($params, $return_type='results', $items_per_page=100, $offset=0) {
        $return_type = ($return_type == 'results') ? 'results' : 'count';

        $columns = array(
            'reports.signature', 'count(reports.id)'
        );
        $tables = array();
        $where = array();

        $platforms = $this->platform_model->getAll();
        foreach ($platforms as $platform) {
            $columns[] = 
                "count(CASE WHEN (reports.os_name = '{$platform->os_name}') THEN 1 END) ".
                "AS is_{$platform->id}";
        }

        $extra_group_by = "";
        if (
            array_key_exists('process_type', $params) && 
	        'plugin' == $params['process_type'] 
        ) {
            array_push($columns, 'plugins.name AS pluginName, plugins_reports.version AS pluginVersion');
            array_push($columns, 'plugins.filename AS pluginFilename');
            $extra_group_by  = "\n, pluginName, pluginVersion, pluginFilename\n";
        }
        array_push($columns, 'SUM (CASE WHEN hangid IS NULL THEN 0  ELSE 1 END) AS numhang');
        array_push($columns, 'SUM (CASE WHEN process_type IS NULL THEN 0  ELSE 1 END) AS numplugin');

        list($from_tables, $join_tables, $where) = 
            $this->_buildCriteriaFromSearchParams($params);

        $sql = "/* soc.web common.queryTopSig. */ ";

        if ($return_type == 'results') {
            $sql .= " SELECT " . join(', ', $columns); 
        } elseif ($return_type == 'count') {
            $sql .= " SELECT COUNT(DISTINCT reports.signature) as count ";
        } 

        $sql .= " FROM   " . join(', ', $from_tables);

        if (count($join_tables) > 0) {
            $sql .= " JOIN  " . join("\nJOIN ", $join_tables);
        }

        $sql .= " WHERE  " . join(' AND ', $where);

        if ($return_type == 'results') {
            $sql .= 
                " GROUP BY reports.signature " .
       	        $extra_group_by .  
                " ORDER BY count(reports.id) DESC " .
                " LIMIT ? " .
                " OFFSET ? "; 
            
            return $this->fetchRows($sql, TRUE, array($items_per_page, $offset));
        } else {
            $results = $this->fetchRows($sql);
            return (isset($results[0]->count)) ? $results[0]->count : 0;
        }
    }

    /**
     * Find total number of crash reports for the given search parameters.
     * @param array Parameters that vary
     * @pager object optional MozPager instance
     * @return int total number of crashes
     */
    public function totalNumberReports($params) {
        list($from_tables, $join_tables, $where) = 
            $this->_buildCriteriaFromSearchParams($params);

        $sql = "/* soc.web common.totalQueryReports */ 
            SELECT COUNT(uuid) as total
            FROM   " . join(', ', $from_tables);
        if(count($join_tables) > 0) {
	    $sql .= " JOIN  " . join("\nJOIN ", $join_tables);
        }

	$sql .= " WHERE  " . join(' AND ', $where);

	$rs = $this->fetchRows($sql);
	if ($rs && count($rs) > 0) {
	    return $rs[0]->total;
	} else {
	    return 0;
	}
    }

    /**
     * Find all crash reports for the given search parameters and
     * paginate the results.
     * 
     * @param array Parameters that vary
     * @pager object optional MozPager instance
     * @return array of objects
     */
    public function queryReports($params, $pager=NULL) {
	if ($pager === NULL) {
	    $pager = new stdClass;
	    $pager->offset = 0;
	    $pager->itemsPerPage = Kohana::config('search.number_report_list');
	    $pager->currentPage = 1;
	}

        $columns = array(
            'reports.date_processed',
            'reports.uptime',
            'reports.user_comments',
            'reports.uuid',
            'reports.product',
            'reports.version',
            'reports.build',
            'reports.signature',
            'reports.url',
            'reports.os_name',
            'reports.os_version',
            'reports.cpu_name',
            'reports.cpu_info',
            'reports.address',
            'reports.reason',
            'reports.last_crash',
            'reports.install_age',
            'reports.hangid',
            'reports.process_type'
        );

        list($from_tables, $join_tables, $where) = 
            $this->_buildCriteriaFromSearchParams($params);

        $sql = "/* soc.web common.queryReports */ 
            SELECT " . join(', ', $columns) .
	    " FROM   " . join(', ', $from_tables);
        if(count($join_tables) > 0) {
	    $sql .= " JOIN  " . join("\nJOIN ", $join_tables);
        }
	$sql .= " WHERE  " . join(' AND ', $where) .
    	        " ORDER BY reports.date_processed DESC 
	          LIMIT ? OFFSET ? ";

        return $this->fetchRows($sql, TRUE, array($pager->itemsPerPage, $pager->offset));
    }

    /**
     * Calculate frequency of crashes across builds and platforms.
     */
    public function queryFrequency($params) {

        $signature = $this->db->escape($params['signature']);

        $columns = array(
            "date_trunc('day', reports.build_date) AS build_date",
            "count(CASE WHEN (reports.signature = $signature) THEN 1 END) AS count",
            "CAST(count(CASE WHEN (reports.signature = $signature) THEN 1 END) AS FLOAT(10)) / count(reports.id) AS frequency", 
            "count(reports.id) AS total"
        );

        $platforms = $this->platform_model->getAll();
        foreach ($platforms as $platform) {
            $columns[] = 
                "count(CASE WHEN (reports.signature = $signature AND reports.os_name = '{$platform->os_name}') THEN 1 END) AS count_{$platform->id}";
            $columns[] = 
                "CASE WHEN (count(CASE WHEN (reports.os_name = '{$platform->os_name}') THEN 1 END) > 0) THEN (CAST(count(CASE WHEN (reports.signature = $signature AND reports.os_name = '{$platform->os_name}') THEN 1 END) AS FLOAT(10)) / count(CASE WHEN (reports.os_name = '{$platform->os_name}') THEN 1 END)) ELSE 0.0 END AS frequency_{$platform->id}";
        }

        list($from_tables, $join_tables, $where) = 
            $this->_buildCriteriaFromSearchParams($params);

        $sql =
            "/* soc.web common.queryFreq */ " .
            " SELECT " . join(', ', $columns) .
            " FROM   " . join(', ', $from_tables);
        if(count($join_tables) > 0) {
	    $sql .= " JOIN  " . join("\nJOIN ", $join_tables);
        }

	$sql .= " WHERE  " . join(' AND ', $where) .
                " GROUP BY date_trunc('day', reports.build_date) ".
                " ORDER BY date_trunc('day', reports.build_date) DESC";

        return $this->fetchRows($sql);
    }

    /**
     * Build the FROM tables, JOIN tables, and WHERE clauses part of a DB query based on search from parameters.
     * @return array of arrays of strings
     *     Example: [['reports'], ['plugins_reports], ['reports.uuid = "blah"]}
     */
    public function _buildCriteriaFromSearchParams($params) {
	$join_tables = array();

        $from_tables = array('reports');
	$where  = array();
	// Bug#518144 - Support retrieving NULL or Empty signatures
	if (isset($params['missing_sig'])) {
	    if ($params['missing_sig'] == Crash::$empty_sig_code) {
		$params['signature'] = '';
	    } else if ($params['missing_sig'] == Crash::$null_sig_code) {
		$where[] = 'reports.signature IS NULL';
		unset($params['signature']);
	    }
	}

        if (isset($params['signature'])) {
            $where[] = 'reports.signature = ' . $this->db->escape($params['signature']);
        }
        
        if (empty($params['date']) || !strtotime($params['date'])) {
            $params['date'] = NULL;
        }

        if (isset($params['version']) && !empty($params['version'])) {
            $or = array();
            foreach ($params['version'] as $spec) {
                if (strstr($spec, ":")) {
                    list($product, $version) = explode(":", $spec);
                    $or[] = 
                        "(reports.product = " . $this->db->escape($product) . " AND " .
                        "reports.version = " . $this->db->escape($version) . ")";
                } else {
                    $or[] = "(reports.product = " . $this->db->escape($spec) . ")";
                }
            }
            $where[] = '(' . join(' OR ', $or) . ')';
        } else if ($params['product']) {
            $or = array();
            foreach ($params['product'] as $product) {
                $or[] = "reports.product = " . $this->db->escape($product);
            }
            $where[] = '(' . join(' OR ', $or) . ')';
        }

        if ($params['branch']) {
            array_push($join_tables, 'branches ON (branches.product = reports.product AND branches.version = reports.version)');
            $or = array();
            foreach ($params['branch'] as $branch) {
                $or[] = "branches.branch = " . $this->db->escape($branch);
            }
            $where[] = '(' . join(' OR ', $or) . ')';
            #$where[] = 'branches.product = reports.product';
            #$where[] = 'branches.version = reports.version';
        }

        if ($params['platform']) {
            $or = array();
            foreach ($params['platform'] as $platform_id) {
                $platform = $this->platform_model->get($platform_id);
                if ($platform) {
                    $or[] = 'reports.os_name = ' . $this->db->escape($platform->os_name);
                }
            }
            $where[] = '(' . join(" OR ", $or) . ')';
        }

        if (isset($params['reason']) && trim($params['reason']) != '') {
            $where[] = ' reports.reason = ' . $this->db->escape($params['reason']); 
        }

        if (array_key_exists('build_id', $params) && $params['build_id']) {
	        $where[] = 'reports.build = ' . $this->db->escape($params['build_id']);
        }

        /* Bug#562375 - Add search support for Hang and OOPP

              | ANY Report Type   | CRASH                | OOPP HANG
  ------------+-------------------+----------------------+---------------
  ANY PROCESS | hang=Any proc=Any | hangid=null proc=Any | hangid = 123 Proc=Any
  ------------+-------------------+----------------------+---------------
      BROWSER | hang=Any proc=Bro | hangid=null proc=Bro | hangid=123 Proc=Bro
  ------------+-------------------+----------------------+---------------
      PLUG-IN | hang=Any proc=Plu | hangid=null proc=Plu | hangid=123 Proc=Plu
	*/

        // Report Type hang_type - [any|crash|hang]
        if (array_key_exists('hang_type', $params) && 
            'crash' == $params['hang_type']) {
                $where[] = 'reports.hangid IS NULL';
	} elseif (array_key_exists('hang_type', $params) && 
		  'hang' == $params['hang_type']) {
                      $where[] = 'reports.hangid IS NOT NULL';
	} // else hang_type is ANY

        // Report Process process_type - [any|browser|plugin|
        if (array_key_exists('process_type', $params) && 
	    'plugin' == $params['process_type'] ) {
            $where[] = "reports.process_type = 'plugin'";

	    array_push($join_tables, 'plugins_reports ON plugins_reports.report_id = reports.id');
	    array_push($join_tables, 'plugins ON plugins_reports.plugin_id = plugins.id');

        if (trim($params['plugin_query']) != '') {
            switch ($params['plugin_query_type']) {
                case 'exact':
                    $plugin_query_term = ' = ' . $this->db->escape($params['plugin_query']); 
                    break;
                case 'startswith':
                    $plugin_query_term = ' LIKE ' . $this->db->escape($params['plugin_query'].'%'); 
                    break;
                case 'contains':
                default:
                    $plugin_query_term = ' LIKE ' . $this->db->escape('%'.$params['plugin_query'].'%'); 
                    break;
            }
            if ('filename' == $params['plugin_field']) {
                $where[] = 'plugins.filename ' . $plugin_query_term;
            } else {
                $where[] = 'plugins.name ' . $plugin_query_term;
            }
        }
	} elseif (array_key_exists('process_type', $params) && 
	          'browser' == $params['process_type']) {
                      $where[] = 'reports.process_type IS NULL';
	} // else process_type is ANY

        if ($params['query']) {

            $term = FALSE;

            switch ($params['query_type']) {
                case 'exact':
                    $term = ' = ' . $this->db->escape($params['query']); break;
                case 'startswith':
                    $term = ' LIKE ' . $this->db->escape($params['query'].'%'); break;
                case 'contains':
                default:
                    $term = ' LIKE ' . $this->db->escape('%'.$params['query'].'%'); break;
            }

            if ($params['query_search'] == 'signature') {
                $where[] = 'reports.signature ' . $term;
            }

        }

        if ($params['range_value'] && $params['range_unit']) {
            if (!$params['date']) {
                $interval = $this->db->escape($params['range_value'] . ' ' . $params['range_unit']);
                $now = date('Y-m-d H:i:s');
                $where[] = "reports.date_processed BETWEEN TIMESTAMP '$now' - CAST($interval AS INTERVAL) AND TIMESTAMP '$now'";
                if (array_key_exists('process_type', $params) && 
                    'plugin' == $params['process_type'] ) {
                        $where[] = "plugins_reports.date_processed BETWEEN TIMESTAMP '$now' - CAST($interval AS INTERVAL) AND TIMESTAMP '$now'";
                }
            } else {
                $date = $this->db->escape($params['date']);
                $interval = $this->db->escape($params['range_value'] . ' ' . $params['range_unit']);
                $where[] = "reports.date_processed BETWEEN CAST($date AS TIMESTAMP WITHOUT TIME ZONE) - CAST($interval AS INTERVAL) AND CAST($date AS TIMESTAMP WITHOUT TIME ZONE)";
                if (array_key_exists('process_type', $params) && 
                    'plugin' == $params['process_type'] ) {
                        $where[] = "plugins_reports.date_processed BETWEEN CAST($date AS TIMESTAMP WITHOUT TIME ZONE) - CAST($interval AS INTERVAL) AND CAST($date AS TIMESTAMP WITHOUT TIME ZONE)";
                }
            }
        }

        return array($from_tables, $join_tables, $where);
    }

}
