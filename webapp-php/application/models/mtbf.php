<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Common model class for managing mean time before failure data
 * in mtbffacts table
 */
class Mtbf_Model extends Model {

  const NUM_DAYS_WINDOW = 60;

  public function getMtbfOf($product, $release_level, $os_name=array('ALL')){
    $sql = "/* soc.web mtbf mtbf proddims */ SELECT productdims.id, productdims.product, productdims.version, productdims.os_name, mtbfconfig.start_dt, mtbfconfig.end_dt from mtbfconfig, productdims
WHERE product = '$product' AND release = '$release_level' AND os_name IN ('" . implode("', '", $os_name) . "') AND mtbfconfig.productdims_id = productdims.id";
    $rs = $this->fetchRows($sql);
    if( count($rs) == 0){
      return array();
    }
    $mtbf = array();
    $indexes = array();
    $prod_id_to_index = array();

    $product_ids = $this->load_product_info($mtbf, $rs, $indexes, $prod_id_to_index);
    $sql = "/* soc.web mtbf mtbf get facts */ SELECT avg_seconds, report_count, day , unique_users, productdims_id FROM mtbffacts WHERE productdims_id IN (" . implode(',', $product_ids) . ") ORDER BY productdims_id, day";

    $rs = $this->fetchRows($sql);

    if( count($rs) == 0){
      return array();
    }
    $this->init_flot_friendly($mtbf);

    foreach($rs as $row){
      $p = $prod_id_to_index[strval($row->productdims_id)];
      $i = $indexes[ strval($row->productdims_id) ];
      $mtbf[$p]['data'][$i][1] = $row->avg_seconds;
      $mtbf[$p]['mtbf-avg'] = $row->report_count;
      $mtbf[$p]['mtbf-report_count'] += $row->report_count;
      $mtbf[$p]['mtbf-unique_users'] += $row->unique_users;
      $indexes[ strval($row->productdims_id) ]++;
    }
    return $mtbf;

  }
    /**
     * Given the results from the database, this function prepares
     * metadata about the mtbf flot JSON friendly object we will
     * be constructing. This function updates
     * $mtbf, $indexes, and $prod_id_to_index with this metadata.
     * 
     * returns an array of product ids
     */
    public function load_product_info(&$mtbf, $rs, &$indexes, &$prod_id_to_index){
      $i = 0;
      $product_ids = array();
      foreach($rs as $row){
        $mtbf[] = array('label' => ($row->product . " " . $row->version), 
                        'mtbf-start-dt' => $row->start_dt,
	                'mtbf-end-dt' => $row->end_dt,
			'mtbf-product-id' => $row->id
  	          );
        if($row->os_name != "ALL"){ 
          $mtbf[$i]['label'] = $mtbf[$i]['label'] . " " . $row->os_name; 
        }
        $indexes[ strval( $row->id ) ] = 0;
        $prod_id_to_index[ strval( $row->id ) ] = $i;
        $product_ids[] = $row->id;
        $i++;
      }
      return $product_ids;
    }
    /**
     * The data in the series has 60 elements like
     * [[0, 33], [1, 60], [2, NULL], [3, NULL]] etc.
     * This function just prepares the array to be populated
     * by database results
     */
    public function init_flot_friendly(&$mtbf){
      for($i=0; $i < count($mtbf); $i++){
        $mtbf[$i]['data'] = array_fill(0, Mtbf_Model::NUM_DAYS_WINDOW, array(0, NULL) );
        $mtbf[$i]['mtbf-report_count'] = 0;
        $mtbf[$i]['mtbf-unique_users'] = 0;
        for($j = 0; $j < count($mtbf[$i]['data']); $j++){
          $mtbf[$i]['data'][$j][0] = $j;
        }
      }

    }
}