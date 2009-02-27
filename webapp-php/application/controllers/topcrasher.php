<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Reporting on top crasher causes
 */
class Topcrasher_Controller extends Controller {

    public function __construct()
    {
        parent::__construct();
        $this->topcrashers_model = new Topcrashers_Model();
    }

    public function index() {
        $branch_data = $this->branch_model->getBranchData();
        $platforms   = $this->platform_model->getAll();

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));

        $this->setViewData(array(
            'all_products'  => $branch_data['products'],
            'all_branches'  => $branch_data['branches'],
            'all_versions'  => $branch_data['versions'],
            'all_platforms' => $platforms
        ));

    }

    public function byversion($product, $version, $build_id=NULL) {
        list($last_updated, $top_crashers) = 
            $this->topcrashers_model->getTopCrashers($product, $version, $build_id);

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));
        if ($this->input->get('format') == "csv") {
  	    $this->setViewData(array('top_crashers' => $this->_csvFormatArray($top_crashers)));
  	    $this->renderCSV("${product}_${version}_" . date("Y-m-d"));
	} else {
          $this->setViewData(array(
              'product'      => $product,
              'version'      => $version,
              'build_id'     => $build_id,
              'last_updated' => $last_updated,
              'top_crashers' => $top_crashers
          ));
	}
    }

    private function _csvFormatArray($topcrashers)
    {
        $csvData = array();
        foreach ($topcrashers as $crash) {
	    $line = array();
	    $sig = strtr($crash->signature, array(
                    ',' => ' ',
                    '\n' => ' ',
		    '"' => '&quot;'
            ));
	    array_push($line, $sig);
	    array_push($line, $crash->total);
	    array_push($line, $crash->win);
	    array_push($line, $crash->mac);
	    array_push($line, $crash->linux);
	    array_push($csvData, $line);
	}
      return $csvData;
    }

    public function bybranch($branch) {

        list($last_updated, $top_crashers) = 
            $this->topcrashers_model->getTopCrashers(NULL, NULL, NULL, $branch);

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));
        if ($this->input->get('format') == "csv") {
  	    $this->setViewData(array('top_crashers' => $this->_csvFormatArray($top_crashers)));
  	    $this->renderCSV("${branch}_" . date("Y-m-d"));
	} else {
            $this->setViewData(array(
                'branch'       => $branch,
                'last_updated' => $last_updated,
                'top_crashers' => $top_crashers
            ));
	}
    }

    public function byurl($product, $version, $build_id=NULL) {
        $by_url_model = new TopcrashersByUrl_Model();
        list($start_date, $end_date, $top_crashers) = 
	  $by_url_model->getTopCrashersByUrl($product, $version);

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));

        $this->setViewData(array(
	    'beginning' => $start_date,
            'ending_on' => $end_date,
            'product'       => $product,
            'version'       => $version,
            'top_crashers'  => $top_crashers
        ));
    }

    public function bydomain($product, $version, $build_id=NULL) {
        $by_url_model = new TopcrashersByUrl_Model();
        list($start_date, $end_date, $top_crashers) = 
	  $by_url_model->getTopCrashersByDomain($product, $version);

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));

        $this->setViewData(array(
	    'beginning' => $start_date,
            'ending_on' => $end_date,
            'product'       => $product,
            'version'       => $version,
            'top_crashers'  => $top_crashers
        ));
    }

    /**
     * AJAX GET method which returns last 2 weeks of 
     * Aggregated crash signatures based on
     * signaturesforurl/{product}/{version}?url={url_encoded_url}&page={page}
     * product - Firefox
     * version - 3.0.3
     * url - http://www.youtube.com/watch
     * page - page offset, defaults to 1
     */
    public function signaturesforurl($product, $version){
      $url = urldecode( $_GET['url']);
      $page = 1;
      if( array_key_exists('page', $_GET)){
        $page = intval($_GET['page']);
      }

      header('Content-Type: text/javascript');
      $this->auto_render = false;
      $by_url_model =  new TopcrashersByUrl_Model();

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));
      
      echo json_encode($by_url_model->getSignaturesByUrl($product, $version, $url, $page));
    }

    /**
     * AJAX GET method which returns all urls under this domain
     * which have had crash reports in the last 2 weeks.
     * urlsfordomain/{product}/{version}?domain={url_encoded_domain}&page={page}
     * product - Firefox
     * version - 3.0.3
     * domain - www.youtube.com
     * page - page offset, defaults to 1
     */
    public function urlsfordomain($product, $version){
      $domain = urldecode( $_GET['domain']);
      $page = 1;
      if( array_key_exists('page', $_GET)){
        $page = intval($_GET['page']);
      }
      header('Content-Type: text/javascript');
      $this->auto_render = false;
      $by_url_model =  new TopcrashersByUrl_Model();

      cachecontrol::set(array(
          'expires' => time() + (60 * 60)
      ));
      
      echo json_encode($by_url_model->getUrlsByDomain($product, $version, $domain, $page));
    }
}
