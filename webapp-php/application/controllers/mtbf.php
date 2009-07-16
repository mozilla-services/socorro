<?php defined('SYSPATH') or die('No direct script access.');

require_once(Kohana::find_file('libraries', 'MY_QueryFormHelper', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'MY_WidgetDataHelper', TRUE, 'php'));
/**
 * This controller displays system status.
 */
class Mtbf_Controller extends Controller {

    /**
     * Displays the MTBF of a specific product build release level
     * product - Firefox, Thunderbird, etc - in product dimension table
     * release_level - one of 'major', 'milestone', or 'development'
     */
    public function of($product, $release_level) {
      $mtbf = new Mtbf_Model;
      $widget = new WidgetDataHelper;
      $mtbf_product_dimensions_config = $widget->convertProductToReleaseMap($mtbf->listReports()); 

      cachecontrol::set(array(
  	  'expires' => time() + (60 * 5) // 5 minutes
      ));

      if( array_key_exists($product, $mtbf_product_dimensions_config )){
        if( in_array($release_level, $mtbf_product_dimensions_config[$product] )){

          $releases = $mtbf->getMtbfOf($product, $release_level);

	  if ($this->input->get('format') == "csv") {
              $eachOs = $mtbf->getMtbfOf($product, $release_level, array('Win', 'Mac', 'Lin', 'Sol'));
              $this->setViewData(array('releases' => $this->_csvFormatArray($releases + $eachOs)));
  	      $this->renderCSV("${product}_${release_level}_" . date("Y-m-d"));
	  } else {
            $this->setViewData(array(
              'title'   => "MTBF of $product ($release_level)",
              'product'   => $product,
              'release_level'   => $release_level,
              'releases'                => $releases,
              'other_releases' => $this->otherReleases($mtbf_product_dimensions_config, $product, $release_level)
            ));
	  }
	}else{

          $this->setViewData(array( 'title' => "MTBF of $product ERROR",
				    'error_message' => "No <strong>$release_level</strong> builds of $product are configured to generate MTBF reports yet."
				   ));
	}
      }else{
	  $productsHelper = new QueryFormHelper;
	  $p2vs = $productsHelper->prepareAllProducts($this->branch_model);
	  if (array_key_exists($product, $p2vs)) {
	      $this->setViewData(array( 'title' => "No MTBF Report",
					'error_message' => "$product is not configured to generate MTBF reports yet."
					));
	  } else {
	      $this->setViewData(array( 'title' => "MTBF ERROR",
					'error_message' => "Unknown product $product "
					));          
	  }

      }
    }

    private function _csvFormatArray($releases) {
        $csvData = array();
	foreach ($releases as $release) {
	    $line = array();
	    array_push($line, $release['label']); 
	    array_push($line, $release['mtbf-start-dt']);
	    array_push($line, $release['mtbf-end-dt']);
	    foreach ($release['data'] as $cell) {
	        $cellValue = is_numeric($cell[1]) ? $cell[1] : 0;
		    array_push($line, $cellValue);
	    }
	    if (count($release['data']) != 60) {
		Kohana::log('alert', "MTBF data should be 60 data points. Was only " . count($release['data']));
	    }
	    array_push($line, $release['mtbf-report_count']);
	    array_push($line, $release['mtbf-unique_users']);
	    array_push($csvData, $line);
	}
	return $csvData;
    }

    public function otherReleases($dims_config, $product, $this_release_level){
      $release_levels = $dims_config[$product];
      $others = array();
      foreach($release_levels as $level){
        if( $level != $this_release_level ){
	  $others[] = $level ;
        }
      }
      return $others;
    }

    /**
     * AJAX GET method which /mtbf/ajax/{product}/{release level}/{OS name}
     * product - name of a product like Firefox or Thunderbird
     * release level - flavor of release [major | milestone | developer]
     * OS name - Optional defaults to ALL, [Win | Mac | ALL | Each]. 
     *           Each will retrieve each of the available OSes
     * returns series of MTBF data JSON encoded
     */
    public function ajax($product, $release_level, $os_name=array('ALL')){
      $widget = new WidgetDataHelper;
      if($os_name == 'Each'){
        $os_name = array('Win', 'Mac', 'Lin', 'Sol');
      }
      header('Content-Type: text/javascript');
      $this->auto_render = false;
      $mtbf = new Mtbf_Model();
      $mtbf_product_dimensions_config = $widget->convertProductToReleaseMap($mtbf->listReports()); 

      cachecontrol::set(array(
	  'expires' => time() + (60 * 5) // 5 minutes
      ));
      if( array_key_exists($product, $mtbf_product_dimensions_config ) &&
          in_array($release_level, $mtbf_product_dimensions_config[$product] )){


          $data = $mtbf->getMtbfOf($product, $release_level, $os_name);
          if( count($data) == 0){
	    $data = array("error" => "No Results");
	  }
          echo json_encode( $data );
      }else{
	Kohana::log('error', "Bad ajax request");
        return json_encode( array('errorMessage' => 'Bad Request, Cannot find valid configuraiton'));
      }
      
    }
}
