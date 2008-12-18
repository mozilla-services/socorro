<?php
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
      //TODO make this config/mtbf.php
      $mtbf_product_dimensions_config = array(
        "Firefox" => array("major", "milestone", "development"),
        "Thunderbird" => array("major", "milestone", "development")
      );

      cachecontrol::set(array(
  	  'expires' => time() + (60 * 5) // 5 minutes
      ));

      if( array_key_exists($product, $mtbf_product_dimensions_config )){
        if( in_array($release_level, $mtbf_product_dimensions_config[$product] )){
          $mtbf = new Mtbf_Model();
          $releases = $mtbf->getMtbfOf($product, $release_level);

          $this->setViewData(array(
            'title'   => "MTBF of $product ($release_level)",
            'product'   => $product,
            'release_level'   => $release_level,
            'releases'                => $releases,
            'other_releases' => $this->otherReleases($mtbf_product_dimensions_config, $product, $release_level)
          ));
	}else{
          $this->setViewData(array( 'title' => "MTBF of $product ERROR",
				    'error_message' => "Unknown build release version $release_level"
				   ));
	}
      }else{
          $this->setViewData(array( 'title' => "MTBF ERROR",
				    'error_message' => "Unknown product $product"
				   ));
      }
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
     * OS name - Optional defaults to ALL, [Win | Mac | ALL]
     * returns series of MTBF data JSON encoded
     */
    public function ajax($product, $release_level, $os_name=array('ALL')){
      if($os_name == 'Each'){
        $os_name = array('Win', 'Mac', 'Lin', 'Sol');
      }
      header('Content-Type: text/javascript');
      $this->auto_render = false;
$mtbf_product_dimensions_config = array(
        "Firefox" => array("major", "milestone", "development"),
        "Thunderbird" => array("major", "milestone", "development")
      );
      cachecontrol::set(array(
	  'expires' => time() + (60 * 5) // 5 minutes
      ));
      if( array_key_exists($product, $mtbf_product_dimensions_config ) &&
          in_array($release_level, $mtbf_product_dimensions_config[$product] )){
          $mtbf = new Mtbf_Model();

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
