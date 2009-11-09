<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Reports based on top crashing signatures
 */
class Topcrasher_Controller extends Controller {

    /**
     * Constructor
     */
    public function __construct()
    {
        parent::__construct();
        $this->topcrashers_model = new Topcrashers_Model();
    }

    /**
     * Generates the index page. In practise this is a sad unhappy page,
     * not used by very many people.
     */
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

    /**
     * Generates the report based on version info
     * 
     * @param string product name 
     * @param string version Example: 3.7a1pre
     * @param int duration in days that this report should cover
     */
    public function byversion($product, $version, $duration=14) {
	$other_durations = array_diff(Kohana::config('topcrashbysig.durations'),
				      array($duration));
	$limit = Kohana::config('topcrashbysig.byversion_limit', 100);
	$top_crashers = array();
	$start = "";
        $last_updated = $this->topcrashers_model->lastUpdatedByVersion($product, $version);

	$percentTotal = 0;
	$totalCrashes = 0;
	if ($last_updated !== FALSE) {
	    $start = $this->topcrashers_model->timeBeforeOffset($duration, $last_updated);
	    $totalCrashes = $this->topcrashers_model->getTotalCrashesByVersion($product, $version, $start, $last_updated);
	    if ($totalCrashes > 0) {
		$top_crashers = $this->topcrashers_model->getTopCrashersByVersion($product, $version, $limit, $start, $last_updated, $totalCrashes);		
		for($i=0; $i < count($top_crashers); $i++) {
		    if( $i==0 ) {
			Kohana::log('info', json_encode($top_crashers[$i]));
		    }
		    $percentTotal += $top_crashers[$i]->percent;
                    if ($this->input->get('format') != "csv") {
			$top_crashers[$i]->percent = number_format($top_crashers[$i]->percent * 100, 2) . "%";
		    }
		}
	    }
	}
       
        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));
        if ($this->input->get('format') == "csv") {
  	    $this->setViewData(array('top_crashers' => $this->_csvFormatArray($top_crashers)));
  	    $this->renderCSV("${product}_${version}_" . date("Y-m-d"));
	} else {
	    $duration_url_path = array(Router::$controller, Router::$method, $product, $version);
	    $this->setViewData(array(
	      'duration_url' => url::site(implode($duration_url_path, '/') . '/'),
              'last_updated' => $last_updated,
	      'other_durations' => $other_durations,
	      'percentTotal' => $percentTotal,
              'product'      => $product,
              'version'      => $version,
	      'start'        => $start,
              'top_crashers' => $top_crashers,
	      'total_crashes' => $totalCrashes
          ));
	}
    }


    /**
     * Helper method for formatting a topcrashers list of objects into data 
     * suitable for CSV output
     * @param array of topCrashersBySignature object
     * @return array of strings
     * @see Topcrashers_Model
     */
    private function _csvFormatArray($topcrashers)
    {
        $csvData = array();
	$i = 0;
        foreach ($topcrashers as $crash) {
	    $line = array();
	    $sig = strtr($crash->signature, array(
                    ',' => ' ',
                    '\n' => ' ',
		    '"' => '&quot;'
            ));
	    array_push($line, $i);
	    array_push($line, $crash->percent);
	    array_push($line, $sig);
	    array_push($line, $crash->total);
	    array_push($line, $crash->win);
	    array_push($line, $crash->mac);
	    array_push($line, $crash->linux);
	    array_push($csvData, $line);
	    $i++;
	}
      return $csvData;
    }

    /**
     * Generates the report based on branch info
     * 
     * @param string branch
     * @param int duration in days that this report should cover
     */
    public function bybranch($branch, $duration = 14) {
	$other_durations = array_diff(Kohana::config('topcrashbysig.durations'),
				      array($duration));
	$limit = Kohana::config('topcrashbysig.bybranch_limit', 100);
	$top_crashers = array();
	$start = "";
        $last_updated = $this->topcrashers_model->lastUpdatedByBranch($branch);

	$percentTotal = 0;
	$totalCrashes = 0;
	if ($last_updated !== FALSE) {
	    $start = $this->topcrashers_model->timeBeforeOffset($duration, $last_updated);
	    $totalCrashes = $this->topcrashers_model->getTotalCrashesByBranch($branch, $start, $last_updated);
	    if ($totalCrashes > 0) {
		$top_crashers = $this->topcrashers_model->getTopCrashersByBranch($branch, $limit, $start, $last_updated, $totalCrashes);
		for($i=0; $i < count($top_crashers); $i++) {
		    $percentTotal += $top_crashers[$i]->percent;
                    if ($this->input->get('format') != "csv") {
		        $top_crashers[$i]->percent = number_format($top_crashers[$i]->percent * 100, 2) . "%";
		    }
		}
	    }
	}
        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));
        if ($this->input->get('format') == "csv") {
  	    $this->setViewData(array('top_crashers' => $this->_csvFormatArray($top_crashers)));
  	    $this->renderCSV("${branch}_" . date("Y-m-d"));
	} else {
	    $duration_url_path = array(Router::$controller, Router::$method, $branch, "");
	    $this->setViewData(array(
                'branch'       => $branch,
		'last_updated' => $last_updated, 
		'percentTotal' => $percentTotal,
		'other_durations' => $other_durations,
	        'duration_url' => url::site(implode($duration_url_path, '/')),
		'start'        => $start,
		'top_crashers' => $top_crashers,
		'total_crashes' => $totalCrashes
				       ));
	}
    }

    /**
     * Generates the report from a URI perspective.
     * URLs are truncated after the query string
     * 
     * @param string product name 
     * @param string version Example: 3.7a1pre
     */
    public function byurl($product, $version) {
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

    /**
     * Generates the report from a domain name perspective
     * 
     * @param string product name 
     * @param string version Example: 3.7a1pre
     */
    public function bydomain($product, $version) {
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
