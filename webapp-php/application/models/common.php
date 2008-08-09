<?php defined('SYSPATH') or die('No direct script access.');
/**
 *
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
     *
     */
    public function _buildCriteriaFromParams($params) {

        $tables = array( 
            'reports' => 1 
        );
        $where  = array(
            'reports.signature IS NOT NULL'
        );

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

        // date, range_value, range_unit
        
        return array($tables, $where);
    }

    /**
     *
            'date'         => date('Y-m-d', time()),
            'range_value'  => '1',
            'range_unit'   => 'weeks',
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
            $this->_buildCriteriaFromParams($params);

        $tables += $params_tables;
        $where  += $params_where;

        $sql =
            " SELECT " . join(', ', $columns) .
            " FROM   " . join(', ', array_keys($tables)) .
            " WHERE  " . join(' AND ', $where) .
            " GROUP BY reports.signature " .
            " ORDER BY count(reports.id) DESC " .
            " LIMIT 100";

        log::debug("queryTopCrashes $sql");

        return $this->db->query($sql);

        $result = $this->db->query($sql);
        $data = array();
        foreach ($result as $row) {
            $data[] = $row;
        }

        return $data;
    }

    /**
     *
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
            $this->_buildCriteriaFromParams($params);

        $tables += $params_tables;
        $where  += $params_where;

        $sql =
            " SELECT " . join(', ', $columns) .
            " FROM   " . join(', ', array_keys($tables)) .
            " WHERE  " . join(' AND ', $where) .
            " ORDER BY reports.date DESC " .
            " LIMIT 500";

        log::debug("queryReports $sql");

        return $this->db->query($sql);

        $result = $this->db->query($sql);
        $data = array();
        foreach ($result as $row) {
            $data[] = $row;
        }

        log::log($data, 'reports', FirePHP::LOG);

        return $data;

    }

    /**
     *
     */
    public function queryFrequency($params) {

    }
/**
SELECT 

    date_trunc(%(date_trunc)s, reports.build_date) AS build_date, 
    
    count(CASE WHEN (reports.signature = %(reports_signature)s) THEN 1 END) AS count, 
    CAST(count(CASE WHEN (reports.signature = %(reports_signature)s) THEN 1 END) AS FLOAT(10)) / count(reports.id) AS frequency, 
    count(reports.id) AS total, 
    
    count(CASE WHEN (reports.signature = %(reports_signature_1)s AND reports.os_name = %(reports_os_name)s) THEN 1 END) AS count_windows, 
    
    CASE WHEN (count(CASE WHEN (reports.os_name = %(reports_os_name)s) THEN 1 END) > %(count)s) THEN (CAST(count(CASE WHEN (reports.signature = %(reports_signature_1)s AND reports.os_name = %(reports_os_name)s) THEN 1 END) AS FLOAT(10)) / count(CASE WHEN (reports.os_name = %(reports_os_name)s) THEN 1 END)) ELSE 0.0 END AS frequency_windows, 
    
    count(CASE WHEN (reports.signature = %(reports_signature_2)s AND reports.os_name = %(reports_os_name_1)s) THEN 1 END) AS count_mac,
    
    CASE WHEN (count(CASE WHEN (reports.os_name = %(reports_os_name_1)s) THEN 1 END) > %(count_1)s) THEN (CAST(count(CASE WHEN (reports.signature = %(reports_signature_2)s AND reports.os_name = %(reports_os_name_1)s) THEN 1 END) AS FLOAT(10)) / count(CASE WHEN (reports.os_name = %(reports_os_name_1)s) THEN 1 END)) ELSE 0.0 END AS frequency_mac, 
    
    count(CASE WHEN (reports.signature = %(reports_signature_3)s AND reports.os_name = %(reports_os_name_2)s) THEN 1 END) AS count_linux, 
    
    CASE WHEN (count(CASE WHEN (reports.os_name = %(reports_os_name_2)s) THEN 1 END) > %(count_2)s) THEN (CAST(count(CASE WHEN (reports.signature = %(reports_signature_3)s AND reports.os_name = %(reports_os_name_2)s) THEN 1 END) AS FLOAT(10)) / count(CASE WHEN (reports.os_name = %(reports_os_name_2)s) THEN 1 END)) ELSE 0.0 END AS frequency_linux, 
    
    count(CASE WHEN (reports.signature = %(reports_signature_4)s AND reports.os_name = %(reports_os_name_3)s) THEN 1 END) AS count_solaris, 

    CASE WHEN (count(CASE WHEN (reports.os_name = %(reports_os_name_3)s) THEN 1 END) > %(count_3)s) THEN (CAST(count(CASE WHEN (reports.signature = %(reports_signature_4)s AND reports.os_name = %(reports_os_name_3)s) THEN 1 END) AS FLOAT(10)) / count(CASE WHEN (reports.os_name = %(reports_os_name_3)s) THEN 1 END)) ELSE 0.0 END AS frequency_solaris 

    FROM reports, branches 

    WHERE reports.build_date IS NOT NULL AND reports.signature IS NOT NULL AND reports.date BETWEEN CAST(%(literal)s AS DATE) - CAST(%(literal_1)s AS INTERVAL) AND CAST(%(literal_2)s AS DATE) AND reports.product = %(reports_product)s AND branches.branch = %(branches_branch)s AND branches.product = reports.product AND branches.version = reports.version AND (reports.product = %(reports_product_1)s AND reports.version = %(reports_version)s OR reports.product = %(reports_product_2)s AND reports.version = %(reports_version_1)s OR reports.product = %(reports_product_3)s AND reports.version = %(reports_version_2)s) AND reports.os_name = %(reports_os_name)s 
    
    GROUP BY date_trunc(%(date_trunc)s, reports.build_date) 
    ORDER BY date_trunc(%(date_trunc)s, reports.build_date) DESC


2008-08-08 23:03:14,671 INFO sqlalchemy.engine.base.Engine.0x..90 {'reports_signature_1': 'js3250.dll@0x1c54f', 'reports_signature_2': 'js3250.dll@0x1c54f', 'reports_signature_3': 'js3250.dll@0x1c54f', 'reports_signature_4': 'js3250.dll@0x1c54f', 'date_trunc': 'day', 'count_3': 0, 'count_2': 0, 'count_1': 0, 'literal': '2008-08-08', 'reports_product_1': 'Firefox', 'reports_product_3': 'Firefox', 'reports_product_2': 'Firefox', 'literal_1': '12 months', 'literal_2': '2008-08-08', 'branches_branch': '1.9', 'reports_product': 'Firefox', 'reports_os_name_1': 'Mac OS X', 'reports_os_name_2': 'Linux', 'reports_os_name_3': 'Solaris', 'reports_version': '3.0b4', 'count': 0, 'reports_os_name': 'Windows NT', 'reports_version_1': '3.0b4pre', 'reports_version_2': '3.0b5pre', 'reports_signature': 'js3250.dll@0x1c54f'}
 


 */

/*

    SELECT reports.signature, count(reports.id), count(CASE WHEN (reports.os_name = %(reports_os_name)s) THEN 1 END) AS is_windows, count(CASE WHEN (reports.os_name = %(reports_os_name_1)s) THEN 1 END) AS is_mac, count(CASE WHEN (reports.os_name = %(reports_os_name_2)s) THEN 1 END) AS is_linux, count(CASE WHEN (reports.os_name = %(reports_os_name_3)s) THEN 1 END) AS is_solaris 
FROM reports 
WHERE reports.signature IS NOT NULL AND reports.signature IS NOT NULL AND reports.date BETWEEN CAST(%(literal)s AS DATE) - CAST(%(literal_1)s AS INTERVAL) AND CAST(%(literal_2)s AS DATE) GROUP BY reports.signature ORDER BY count(reports.id) DESC 
 LIMIT 100
2008-08-08 18:25:56,422 INFO sqlalchemy.engine.base.Engine.0x..10 {'reports_os_name': 'Windows NT', 'literal': '2008-08-13', 'reports_os_name_1': 'Mac OS X', 'reports_os_name_2': 'Linux', 'reports_os_name_3': 'Solaris', 'literal_1': '12 months', 'literal_2': '2008-08-13'}


 
SELECT reports.signature, count(reports.id), count(CASE WHEN (reports.os_name = %(reports_os_name)s) THEN 1 END) AS is_windows, count(CASE WHEN (reports.os_name = %(reports_os_name_1)s) THEN 1 END) AS is_mac, count(CASE WHEN (reports.os_name = %(reports_os_name_2)s) THEN 1 END) AS is_linux, count(CASE WHEN (reports.os_name = %(reports_os_name_3)s) THEN 1 END) AS is_solaris 
FROM reports, branches 
WHERE reports.signature IS NOT NULL AND 
reports.signature IS NOT NULL AND 
reports.date BETWEEN now() - CAST(%(literal)s AS INTERVAL) AND now() AND 
reports.product = %(reports_product)s AND 
branches.branch = %(branches_branch)s AND 
branches.product = reports.product AND 
branches.version = reports.version AND 
reports.product = %(reports_product_1)s AND 
reports.version = %(reports_version)s AND 
reports.os_name = %(reports_os_name)s AND 
reports.signature LIKE %(reports_signature)s 
GROUP BY reports.signature 
ORDER BY count(reports.id) DESC 
 LIMIT 100
 
 2008-08-08 16:15:54,113 INFO sqlalchemy.engine.base.Engine.0x..10 {'reports_os_name': 'Windows NT', 'reports_product': 'Firefox', 'literal': '12 months', 'reports_signature': '%stackastack%', 'reports_product_1': 'Firefox', 'reports_os_name_1': 'Mac OS X', 'reports_os_name_2': 'Linux', 'reports_os_name_3': 'Solaris', 'branches_branch': '1.9', 'reports_version': '3.0b4pre'}


SELECT reports.signature, count(reports.id), count(CASE WHEN (reports.os_name = %(reports_os_name)s) THEN 1 END) AS is_windows, count(CASE WHEN (reports.os_name = %(reports_os_name_1)s) THEN 1 END) AS is_mac, count(CASE WHEN (reports.os_name = %(reports_os_name_2)s) THEN 1 END) AS is_linux, count(CASE WHEN (reports.os_name = %(reports_os_name_3)s) THEN 1 END) AS is_solaris 
FROM reports, branches 
WHERE reports.signature IS NOT NULL AND reports.signature IS NOT NULL AND reports.date BETWEEN now() - CAST(%(literal)s AS INTERVAL) AND now() AND reports.product = %(reports_product)s AND branches.branch = %(branches_branch)s AND branches.product = reports.product AND branches.version = reports.version AND reports.product = %(reports_product_1)s AND reports.version = %(reports_version)s AND reports.os_name = %(reports_os_name)s AND reports.signature = %(reports_signature)s GROUP BY reports.signature ORDER BY count(reports.id) DESC 
 LIMIT 100
2008-08-08 16:19:11,895 INFO sqlalchemy.engine.base.Engine.0x..10 {'reports_os_name': 'Windows NT', 'reports_product': 'Firefox', 'literal': '12 months', 'reports_signature': 'stackastack', 'reports_product_1': 'Firefox', 'reports_os_name_1': 'Mac OS X', 'reports_os_name_2': 'Linux', 'reports_os_name_3': 'Solaris', 'branches_branch': '1.9', 'reports_version': '3.0b4pre'}


 SELECT reports.signature, count(reports.id), count(CASE WHEN (reports.os_name = %(reports_os_name)s) THEN 1 END) AS is_windows, count(CASE WHEN (reports.os_name = %(reports_os_name_1)s) THEN 1 END) AS is_mac, count(CASE WHEN (reports.os_name = %(reports_os_name_2)s) THEN 1 END) AS is_linux, count(CASE WHEN (reports.os_name = %(reports_os_name_3)s) THEN 1 END) AS is_solaris 
FROM reports, branches 
WHERE reports.signature IS NOT NULL AND reports.signature IS NOT NULL AND reports.date BETWEEN now() - CAST(%(literal)s AS INTERVAL) AND now() AND reports.product = %(reports_product)s AND branches.branch = %(branches_branch)s AND branches.product = reports.product AND branches.version = reports.version AND reports.product = %(reports_product_1)s AND reports.version = %(reports_version)s AND reports.os_name = %(reports_os_name)s AND reports.signature LIKE %(reports_signature)s GROUP BY reports.signature ORDER BY count(reports.id) DESC 
 LIMIT 100
2008-08-08 16:19:35,173 INFO sqlalchemy.engine.base.Engine.0x..10 {'reports_os_name': 'Windows NT', 'reports_product': 'Firefox', 'literal': '12 months', 'reports_signature': 'stackastack%', 'reports_product_1': 'Firefox', 'reports_os_name_1': 'Mac OS X', 'reports_os_name_2': 'Linux', 'reports_os_name_3': 'Solaris', 'branches_branch': '1.9', 'reports_version': '3.0b4pre'}


SELECT reports.signature, count(reports.id), count(CASE WHEN (reports.os_name = %(reports_os_name)s) THEN 1 END) AS is_windows, count(CASE WHEN (reports.os_name = %(reports_os_name_1)s) THEN 1 END) AS is_mac, count(CASE WHEN (reports.os_name = %(reports_os_name_2)s) THEN 1 END) AS is_linux, count(CASE WHEN (reports.os_name = %(reports_os_name_3)s) THEN 1 END) AS is_solaris 
FROM reports, branches 
WHERE reports.signature IS NOT NULL AND reports.signature IS NOT NULL AND reports.date BETWEEN now() - CAST(%(literal)s AS INTERVAL) AND now() AND reports.product = %(reports_product)s AND branches.branch = %(branches_branch)s AND branches.product = reports.product AND branches.version = reports.version AND reports.product = %(reports_product_1)s AND reports.version = %(reports_version)s AND reports.os_name = %(reports_os_name)s AND (EXISTS (SELECT 1 
FROM frames 
WHERE frames.signature LIKE %(frames_signature)s AND frames.report_id = reports.id)) GROUP BY reports.signature ORDER BY count(reports.id) DESC 
 LIMIT 100
2008-08-08 16:25:16,107 INFO sqlalchemy.engine.base.Engine.0x..10 {'frames_signature': 'stackastack%', 'reports_os_name': 'Windows NT', 'reports_product': 'Firefox', 'literal': '12 months', 'reports_product_1': 'Firefox', 'reports_os_name_1': 'Mac OS X', 'reports_os_name_2': 'Linux', 'reports_os_name_3': 'Solaris', 'branches_branch': '1.9', 'reports_version': '3.0b4pre'}



 */


}
