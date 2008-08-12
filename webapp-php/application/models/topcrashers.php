<?php
/**
 * Manage data in the topcrashers table.
 */
class Topcrashers_Model extends Model {

    /**
     * Find top crashes from the aggregate topcrashers table.
     */
    public function getTopCrashers($product=NULL, $version=NULL, $build_id=NULL, $branch=NULL) {

        $tables = array( 'topcrashers' => 1 );
        $where  = array();

        if ($product)
            $where[] = 'product=' . $this->db->escape($product);

        if ($version)
            $where[] = 'version=' . $this->db->escape($version);
        
        if ($build_id)
            $where[] = 'build=' . $this->db->escape($build_id);
        
        if ($branch) {
            $tables['branches'] = 1;
            $where[] = 'branches.branch = ' . $this->db->escape($branch);
            $where[] = 'branches.product = topcrashers.product';
            $where[] = 'branches.version = topcrashers.version';
        }

        // Find the time when the table was last updated, limit to that update.
        $update_sql = 
            " SELECT topcrashers.last_updated AS last_updated".
            " FROM " . join(', ', array_keys($tables)) .
            " WHERE " . join(' AND ', $where) .
            " ORDER BY last_updated DESC LIMIT 1 ";
        $rows = $this->fetchRows($update_sql);
        if ($rows) {
            $last_updated = $rows[0]->last_updated;
            $where[] = 'last_updated=' . $this->db->escape($last_updated);
        } else {
            $last_updated = '';
        }

        $sql =
            " SELECT topcrashers.* " .
            " FROM " . join(', ', array_keys($tables)) .
            " WHERE  " . join(' AND ', $where) .
            " ORDER BY total DESC ";

        return array($last_updated, $this->fetchRows($sql));
    }

}
