<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Common model class for managing mean time before failure data
 * in mtbffacts table
 */
class Mtbf_Model extends Model {

  const NUM_DAYS_WINDOW = 60;

  public function getMtbfOf($product, $release_level, $os_name=array()){
    $osNameList = implode(",", array_map(array($this->db, 'escape'), $os_name));
    $p = $this->db->escape($product);
    $r = $this->db->escape($release_level);

    $where = array("p.product = $p", "p.release = $r"); 
    $query_name = "mtbf mtbf proddims";
    $by_os = count($os_name) > 0;
    if ($by_os) {
      $where[] = 'o.os_name IN (' . $osNameList . ')';
	$group_by = 'GROUP BY p.id, p.product, p.version, pv.productdims_id, o.os_name, day, pv.start_date, pv.end_date';
        $os_name = "o.os_name, ";
        $query_name .= " byos";
    } else {
        $group_by = 'GROUP BY p.id, p.product, p.version, pv.productdims_id, day, pv.start_date, pv.end_date';
	$os_name = "";
    }

    $sql = "/* soc.web $query_name */ 
     SELECT p.id, p.product, p.version, 
       $os_name 
       pv.start_date,pv.end_date,
       cast(f.window_end - f.window_size as date) as day,
       cast(sum(f.sum_uptime_seconds)/sum(f.report_count) as integer) as avg_seconds,
       sum(f.report_count) as report_count,
       pv.productdims_id
       from time_before_failure f
       JOIN productdims p ON f.productdims_id = p.id
       JOIN osdims o ON f.osdims_id = o.id
       JOIN product_visibility pv ON p.id = pv.productdims_id
       WHERE " . join(' AND ', $where) . "
       $group_by  
       ORDER BY p.id, day;";

    $rs = $this->fetchRows($sql);
    if( count($rs) == 0){
      return array();
    }
    $mtbf = array();

    $prod_id_to_index = array();

    $this->load_product_info($mtbf, $rs, $prod_id_to_index, $by_os);
    
    for ($i = 0; $i < count($mtbf); $i++) {
        $release = $mtbf[$i];
        $crashes = 0;
	$uptime = 0;
	$nodes = 0;
	foreach ($release['mtbf-avg'] as $a) {
            $crashes += $a[0];
	    $nodes ++;
	    $uptime  += $a[1];
	}
	$mtbf[$i]['mtbf-report_count'] = $crashes;
	if ($nodes > 0) {
	    // Im not sure we can do this... we've already avg for each day and now we are avg the avgs
	    $mtbf[$i]['mtbf-avg'] = $uptime / $nodes;
	} else {
	    Kohana::log('error', "Unable to average uptime across crashes, crashes=$crashes uptime=$uptime");
            $mtbf[$i]['mtbf-avg'] = 0;
	}
	$i++;
    }
    return $mtbf;
  }
    /**
     * Given the results from the database, this function prepares
     * metadata about the mtbf flot JSON friendly object we will
     * be constructing. This function updates
     * $mtbf, $prod_id_to_index with this metadata.
     *
     * Results are either segmented by product/version or at a finer grain
     * by product/version/os name
     */
    public function load_product_info(&$mtbf, $rs, &$prod_id_to_index, $by_os){
	foreach($rs as $row){
	    if ($by_os) {
	        $prod_id = strval($row->productdims_id) . $row->os_name;
	    } else {
	        $prod_id = strval($row->productdims_id);
	    }

	    /* is this a product we haven't seen yet? */
	    if (! array_key_exists($prod_id, $prod_id_to_index)) {
	        // the $mtbf array is initially empty...
	        $prod_id_to_index[$prod_id] = $i = count($mtbf);
		#  $i = $prod_id_to_index[$prod_id];
                $mtbf[] = array('label'             => ($row->product . " " . $row->version), 
                                'mtbf-start-dt'     => $row->start_date,
	                        'mtbf-end-dt'       => $row->end_date,
		                'mtbf-product-id'   => $row->id,
                                'mtbf-report_count' => $row->report_count,
				'mtbf-unique_users' => 0,
                                'mtbf-avg'          => array(array($row->report_count, $row->avg_seconds)),
				'data'              => array( array(0, $row->avg_seconds) )
  	        );
		if ($by_os) {
		    $mtbf[$i]['label'] = $mtbf[$i]['label'] . " " . $row->os_name;
		}
	    } else {
	        $i = $prod_id_to_index[$prod_id];
		$mtbf[$i]['data'][] = array( $i, $row->avg_seconds);
                $mtbf[$i]['mtbf-avg'][] = array($row->report_count, $row->avg_seconds);
                $mtbf[$i]['mtbf-report_count'] += $row->report_count;
	    }
	}
    }

    /**
     * Returns a list of existing reports based on the 
     * product_visibility table
     */
    public function listReports($product=NULL)
    {
        $whereClause = $product == NULL ? "" : "WHERE product = " . $this->db->escape($product);

        $sql = "SELECT distinct p.product, p.release FROM product_visibility conf
                    JOIN productdims p ON conf.productdims_id = p.id
                    $whereClause
                    ORDER BY product, release;";

        return $this->fetchRows($sql);
    }
}