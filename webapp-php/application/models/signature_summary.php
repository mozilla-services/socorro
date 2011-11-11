<?php

class Signature_Summary_Model extends Model {

    protected $_sig_cache = array();

    public function getOSCounts($signature, $start, $end)
    {
        $signature_c = $this->search_signature_table($signature);
        if(!is_numeric($signature_c)) {
            return FALSE;
        }
        $start_c = $this->db->escape($start);
        $end_c = $this->db->escape($end);
        $sql = "WITH counts AS (
            SELECT os_version_string, report_count,
                    sum(report_count) over () as total_count
                        FROM os_signature_counts
                            WHERE signature_id = $signature_c
                                    AND report_date BETWEEN $start_c and $end_c
                                    )
        SELECT os_version_string, 
            round(sum(report_count)*100/max(total_count)::numeric, 1) as report_percent,
                sum(report_count) as report_count
                FROM counts
                GROUP BY os_version_string
                HAVING sum(report_count)*100/max(total_count)::numeric >= 1.0
                ORDER BY report_count DESC";
        return $this->db->query($sql)->as_array();
    }

    public function getUptimeCounts($signature, $start, $end)
    {
       $signature_c = $this->search_signature_table($signature);
       if(!is_numeric($signature_c)) {
           return FALSE;
       } 
       $start_c = $this->db->escape($start);
       $end_c = $this->db->escape($end);
        $sql = "WITH counts AS (
            SELECT uptime_level, report_count,
                    sum(report_count) over () as total_count
                        FROM uptime_signature_counts
                            WHERE signature_id = $signature_c
                                    AND report_date BETWEEN $start_c and $end_c
                                    )
        SELECT uptime_string, 
            round(sum(report_count)*100/max(total_count)::numeric, 1) as report_percent,
                sum(report_count) as report_count
                FROM counts
                    JOIN uptime_levels USING (uptime_level)
                    GROUP BY uptime_string
                    HAVING sum(report_count)*100/max(total_count)::numeric >= 1.0
                    ORDER BY report_count DESC";

        return $this->db->query($sql)->as_array();
    }

    public function getProductCounts($signature, $start, $end)
    {
       $signature_c = $this->search_signature_table($signature);
       if(!is_numeric($signature_c)) {
            return FALSE;
        }
        $start_c = $this->db->escape($start);
        $end_c = $this->db->escape($end);
        $sql = "WITH counts AS (
            SELECT product_version_id, report_count,
                    sum(report_count) over () as total_count
                        FROM product_signature_counts
                            WHERE signature_id = $signature_c
                                    AND report_date BETWEEN $start_c and $end_c
                                    )
        SELECT product_name,  version_string, 
            round(sum(report_count)*100/max(total_count)::numeric, 1) as report_percent,
                sum(report_count) as report_count
                FROM counts
                    JOIN product_versions USING (product_version_id)
                    GROUP BY product_name, version_string
                    HAVING sum(report_count)*100/max(total_count)::numeric >= 1.0
                    ORDER BY report_percent DESC";

        return $this->db->query($sql)->as_array();
    }

    public function search_signature_table($signature_string)
    {
        if(isset($this->sig_cache[$signature_string])) {
            return $this->sig_cache[$signature_string];
        }

        $ss_c = $this->db->escape($signature_string);
        $sql = "SELECT signature_id FROM signatures WHERE signature = $ss_c";
        $result = $this->db->query($sql)->as_array();
        if($result) {
            $val = $result[0]->signature_id;
            $this->sig_cache[$signature_string] = $val;
            return $val;
        } else {
            return FALSE;
        }
    }
}
