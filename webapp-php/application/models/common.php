<?php defined('SYSPATH') or die('No direct script access.');
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
     * Find top report signatures for the given search parameters.
     */
    public function queryTopSignatures($params) {

        $columns = array(
            'reports.signature', 'count(reports.id)'
        );
        $tables = array(
        );
        $where = array(
        );

        $platforms = $this->platform_model->getAll();
        foreach ($platforms as $platform) {
            $columns[] = 
                "count(CASE WHEN (reports.os_name = '{$platform->os_name}') THEN 1 END) ".
                "AS is_{$platform->id}";
        }

        list($params_tables, $params_where) = 
            $this->_buildCriteriaFromSearchParams($params);

        $tables += $params_tables;
        $where  += $params_where;

        $sql =
            " SELECT " . join(', ', $columns) .
            " FROM   " . join(', ', array_keys($tables)) .
            " WHERE  " . join(' AND ', $where) .
            " GROUP BY reports.signature " .
            " ORDER BY count(reports.id) DESC " .
            " LIMIT 100";

        return $this->fetchRows($sql);
    }

    /**
     * Find reports for the given search parameters.
     */
    public function queryReports($params) {

        $columns = array(
            'reports.date',
            'reports.date_processed',
            'reports.uptime',
            'reports.comments',
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
            'reports.install_age'
        );
        $tables = array(
        );
        $where = array(
        );

        list($params_tables, $params_where) = 
            $this->_buildCriteriaFromSearchParams($params);

        $tables += $params_tables;
        $where  += $params_where;

        $sql =
            " SELECT " . join(', ', $columns) .
            " FROM   " . join(', ', array_keys($tables)) .
            " WHERE  " . join(' AND ', $where) .
	  " ORDER BY reports.date DESC " .
	  " LIMIT 500";

        return $this->fetchRows($sql);
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
        $tables = array(
        );
        $where = array(
        );

        $platforms = $this->platform_model->getAll();
        foreach ($platforms as $platform) {
            $columns[] = 
                "count(CASE WHEN (reports.signature = $signature AND reports.os_name = '{$platform->os_name}') THEN 1 END) AS count_{$platform->id}";
            $columns[] = 
                "CASE WHEN (count(CASE WHEN (reports.os_name = '{$platform->os_name}') THEN 1 END) > 0) THEN (CAST(count(CASE WHEN (reports.signature = $signature AND reports.os_name = '{$platform->os_name}') THEN 1 END) AS FLOAT(10)) / count(CASE WHEN (reports.os_name = '{$platform->os_name}') THEN 1 END)) ELSE 0.0 END AS frequency_{$platform->id}";
        }

        list($params_tables, $params_where) = 
            $this->_buildCriteriaFromSearchParams($params);

        $tables += $params_tables;
        $where  += $params_where;

        $sql =
            " SELECT " . join(', ', $columns) .
            " FROM   " . join(', ', array_keys($tables)) .
            " WHERE  " . join(' AND ', $where) .
            " GROUP BY date_trunc('day', reports.build_date) ".
            " ORDER BY date_trunc('day', reports.build_date) DESC";

        return $this->fetchRows($sql);
    }

    /**
     * Build the WHERE part of a DB query based on search from parameters.
     */
    public function _buildCriteriaFromSearchParams($params) {

        $tables = array( 
            'reports' => 1 
        );
        $where  = array(
            'reports.signature IS NOT NULL'
        );

        if (isset($params['signature'])) {
            $where[] = 'reports.signature = ' . $this->db->escape($params['signature']);
        }

        if ($params['product']) {
            $or = array();
            foreach ($params['product'] as $product) {
                $or[] = "reports.product = " . $this->db->escape($product);
            }
            $where[] = '(' . join(' OR ', $or) . ')';
        }

        if ($params['branch']) {
            $tables['branches'] = 1;
            $or = array();
            foreach ($params['branch'] as $branch) {
                $or[] = "branches.branch = " . $this->db->escape($branch);
            }
            $where[] = '(' . join(' OR ', $or) . ')';
            $where[] = 'branches.product = reports.product';
            $where[] = 'branches.version = reports.version';
        }

        if ($params['version']) {
            $or = array();
            foreach ($params['version'] as $spec) {
                list($product, $version) = split(':', $spec);
                $or[] = 
                    "(reports.product = " . $this->db->escape($product) . " AND " .
                    "reports.version = " . $this->db->escape($version) . ")";
            }
            $where[] = '(' . join(' OR ', $or) . ')';
        }

        if ($params['platform']) {
            foreach ($params['platform'] as $platform_id) {
                $platform = $this->platform_model->get($platform_id);
                if ($platform) {
                    $where[] = 'reports.os_name = ' . $this->db->escape($platform->os_name);
                }
            }
        }

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
            } else if ($params['query_search'] == 'stack') {
                $where[] = "(EXISTS (" .
                    "SELECT 1 FROM frames " . 
                    "WHERE frames.signature $term " .
                    "AND frames.report_id = reports.id" .
                    "))";
            }

        }

        if ($params['range_value'] && $params['range_unit']) {
            if (!$params['date']) {
                $interval = $this->db->escape($params['range_value'] . ' ' . $params['range_unit']);
                $where[] = "reports.date BETWEEN now() - CAST($interval AS INTERVAL) AND now()";
            } else {
                $date = $this->db->escape($params['date']);
                $interval = $this->db->escape($params['range_value'] . ' ' . $params['range_unit']);
                $where[] = "reports.date BETWEEN CAST($date AS DATE) - CAST($interval AS INTERVAL) AND CAST($date AS DATE)";
            }
        }
        
        return array($tables, $where);
    }

}
