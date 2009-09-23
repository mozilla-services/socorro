<?php
/**
 * Manage data in the topcrashers table.
 */
class Topcrashers_Model extends Model {

    /**
     * Find top crashes from the aggregate topcrashers table.
     */
  public function getTopCrashers($product=NULL, $version=NULL, $build_id=NULL, $branch=NULL, $limit=100) {

        $tables = array( 'top_crashes_by_signature tcs' => 1 );
        $where  = array();

        if ($product)
            $where[] = 'p.product=' . $this->db->escape($product);

        if ($version)
            $where[] = 'p.version=' . $this->db->escape($version);

        $join = "JOIN productdims p ON tcs.productdims_id = p.id ";
        
        /* TODO unsupported? if ($build_id)
	 $where[] = 'build=' . $this->db->escape($build_id); */
        
        if ($branch) {

	    $join .= "\nJOIN  branches USING (product, version) ";

            //$tables['branches'] = 1;
            $where[] = 'branches.branch = ' . $this->db->escape($branch);
            //$where[] = 'branches.product = topcrashers.product';
            //$where[] = 'branches.version = topcrashers.version';
        }

        // Find the time when the table was last updated, limit to that update.
        $update_sql = 
            "/* soc.web topcrash.lastupdate */ 
              SELECT max(window_end) AS last_updated
              FROM " . join(', ', array_keys($tables)) . "
              $join
              WHERE " . join(' AND ', $where);
        $rows = $this->fetchRows($update_sql);
        if ($rows) {
	  $last_updated = $rows[0]->last_updated;
	  // make a 2 week window
	  $last_updated = date("Y-m-d H:i:s", 
			       strtotime($last_updated ) - (60 * 60 * 24 * 14) + 1);
	  $where[] = "window_end >= " . $this->db->escape($last_updated);

        } else {
            $last_updated = '';
        }
	$join = "JOIN productdims p ON tcs.productdims_id = p.id
                 JOIN osdims o ON tcs.osdims_id = o.id ";

        if ($branch) {
	  $join .= "\nJOIN branches USING (product, version) ";
	}

        $sql =
            "/* soc.web topcrash.topcrasherss */ 
             SELECT
                 p.product AS product,
                 p.version AS version,
                 tcs.signature,
                 sum(tcs.count) as total,
                 sum(case when o.os_name = 'Windows NT' then tcs.count else 0 end) as win,
                 sum(case when o.os_name = 'Mac OS X' then tcs.count else 0 end) as mac,
                 sum(case when o.os_name = 'Linux' then tcs.count else 0 end) as linux 
             FROM " . join(', ', array_keys($tables)) . "
             $join
             WHERE  " . join(' AND ', $where) . "
             GROUP BY 
                 p.product, p.version, tcs.signature
             HAVING  
                 sum(tcs.count) > 0
             ORDER BY 
                 total desc
             LIMIT $limit";
        return array($last_updated, $this->fetchRows($sql));
    }

}
