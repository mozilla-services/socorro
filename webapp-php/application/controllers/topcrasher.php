<?php defined('SYSPATH') or die('No direct script access.');

require_once(Kohana::find_file('libraries', 'bugzilla', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'release', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'timeutil', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'versioncompare', TRUE, 'php'));

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
        $this->bug_model = new Bug_Model;
    }

    /**
     * Generates the index page.
     */
    public function index() {
        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));

        $featured = Kohana::config('dashboard.feat_nav_products');
        $all_products = $this->currentProducts();

        $i = 0;
        $crasher_data = array();
        foreach ($featured as $prod_name) {
            foreach (array(Release::MAJOR, Release::DEVELOPMENT,
                Release::MILESTONE) as $release) {
                if (empty($all_products[$prod_name][$release])) continue;
                if (++$i > 4) break 2;

                $version = $all_products[$prod_name][$release];
                $crasher_data[] = array(
                    'product' => $prod_name,
                    'version' => $version,
                    'crashers' => $this->_getTopCrashers($prod_name, $version)
                    );
            }
        }

        // generate list of all versions
        $branches = new Branch_Model();
        $prod_versions = $branches->getProductVersions();
        $all_versions = array();
        foreach ($prod_versions as $ver) {
            $all_versions[$ver->product][] = $ver->version;
        }
        // sort
        $vc = new VersioncompareComponent();
        foreach (array_keys($all_versions) as $prod) {
            $vc->sortAppversionArray($all_versions[$prod]);
            $all_versions[$prod] = array_reverse($all_versions[$prod]);
        }

        $this->setViewData(array(
            'crasher_data' => $crasher_data,
            'all_versions'  => $all_versions,
            'sig_sizes'  => Kohana::config('topcrashers.numberofsignatures'),
        ));
    }

    /**
     * get top crashers for a given product and version
     */
    private function _getTopCrashers($product, $version) {
        $sigSize = Kohana::config("topcrashers.numberofsignatures");
        $maxSigSize = max($sigSize);

        $end = $this->topcrashers_model->lastUpdatedByVersion($product, $version);
        $start = $this->topcrashers_model->timeBeforeOffset(14, $end);

        return $this->topcrashers_model->getTopCrashersByVersion($product, $version, $maxSigSize, $start, $end);
    }

    /**
     * Generates the report based on version info
     * 
     * @param string product name 
     * @param string version Example: 3.7a1pre
     * @param int duration in days that this report should cover
     */
    public function byversion_old($product='', $version='', $duration=14) {
        if (empty($product)) $product = @$_GET['product'];
        if (empty($version)) $version = @$_GET['version'];

	$other_durations = array_diff(Kohana::config('topcrashbysig.durations'),
				      array($duration));
	$limit = Kohana::config('topcrashbysig.byversion_limit', 100);
	$top_crashers = array();
	$start = "";
	$before = microtime(TRUE);
        $last_updated = $this->topcrashers_model->lastUpdatedByVersion($product, $version);

	$percentTotal = 0;
	$totalCrashes = 0;

        $signature_to_bugzilla = array();
	$signatures = array();

	if ($last_updated !== FALSE) {
	    $this->navigationChooseVersion($product, $version);
	    $start = $this->topcrashers_model->timeBeforeOffset($duration, $last_updated);
	    $totalCrashes = $this->topcrashers_model->getTotalCrashesByVersion($product, $version, $start, $last_updated);
	    if ($totalCrashes > 0) {
		$top_crashers = $this->topcrashers_model->getTopCrashersByVersion($product, $version, $limit, $start, $last_updated, $totalCrashes);			
		$after = microtime(TRUE);
		Kohana::log('info', "Finished DB access in " . (($after - $before) / 1) . " seconds which is $after - $before");
		for($i=0; $i < count($top_crashers); $i++) {
		    if( $i==0 ) {
			Kohana::log('info', json_encode($top_crashers[$i]));
		    }
		    $percentTotal += $top_crashers[$i]->percent;
                    if ($this->input->get('format') != "csv") {
			$top_crashers[$i]->percent = number_format($top_crashers[$i]->percent * 100, 2) . "%";
			array_push($signatures, $top_crashers[$i]->signature);
		    }
		}
		$rows = $this->bug_model->bugsForSignatures(array_unique($signatures));
		$bugzilla = new Bugzilla;
		$signature_to_bugzilla = $bugzilla->signature2bugzilla($rows, Kohana::config('codebases.bugTrackingUrl'));
	    }
	}

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));
        if ($this->input->get('format') == "csv") {
  	    $this->setViewData(array('top_crashers' => $this->_csvFormatOldArray($top_crashers)));
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
	      'sig2bugs' => $signature_to_bugzilla,
	      'start'        => $start,
              'top_crashers' => $top_crashers,
	      'total_crashes' => $totalCrashes
          ));
	}
    }

    public function byversion($product, $version, $duration=14)
    {
	$duration_url_path = array(Router::$controller, Router::$method, $product, $version);
	$other_durations = array_diff(Kohana::config('topcrashbysig.durations'),
				      array($duration));

	$config = array();
	$credentials = Kohana::config('webserviceclient.basic_auth');
	if ($credentials) {
	    $config['basic_auth'] = $credentials;
	}
	$service = new Web_Service($config);

	$host = Kohana::config('webserviceclient.socorro_hostname');

	$cache_in_minutes = Kohana::config('webserviceclient.topcrash_vers_rank_cache_minutes', 60);
	$end_date = urlencode(date('o-m-d\TH:i:s\T+0000', TimeUtil::roundOffByMinutes($cache_in_minutes)));
	// $dur is number of hours 
	$dur = $duration * 24;
	$limit = Kohana::config('topcrashbysig.byversion_limit', 300);
	// lifetime in seconds
	$lifetime = $cache_in_minutes * 60;

	$p = urlencode($product);
	$v = urlencode($version);
        $resp = $service->get("${host}/200911/topcrash/sig/trend/rank/p/${p}/v/${v}/end/${end_date}/duration/${dur}/listsize/${limit}",
			      'json', $lifetime);
	if($resp) {
	    $this->_ensureProperties($resp, array(
				     'start_date' => '',
				     'end_date' => '',
				     'totalPercentage' => 0,
				     'crashes' => array(),
				     'totalNumberOfCrashes' => 0), 'top crash sig overall');

	    $signatures = array();
	    $req_props = array( 'signature' => '', 'count' => 0, 
				'win_count' => 0, 'mac_count' => 0, 'linux_count' => 0,
				'currentRank' => 0, 'previousRank' => 0, 'changeInRank' => 0, 
				'percentOfTotal' => 0, 'previousPercentOfTotal' => 0, 'changeInPercentOfTotal' => 0);

	    foreach($resp->crashes as $top_crasher) {
		$this->_ensureProperties($top_crasher, $req_props, 'top crash sig trend crashes');

		if ($this->input->get('format') != "csv") {
		    $top_crasher->{'display_percent'} = number_format($top_crasher->percentOfTotal * 100, 2) . "%";
		    $top_crasher->{'display_previous_percent'} = number_format($top_crasher->previousPercentOfTotal * 100, 2) . "%";
		    $top_crasher->{'display_change_percent'} = number_format($top_crasher->changeInPercentOfTotal * 100, 2) . "%";

		    array_push($signatures, $top_crasher->signature);
		}

		$change = $top_crasher->changeInRank;
		$top_crasher->trendClass = "new";
		if (is_numeric($change)) {
		    if ($change > 0) {
			$top_crasher->trendClass = "up";
		    } else {
			$top_crasher->trendClass = "down";
		    }
		    if (abs($change) < 5) {
			$top_crasher->trendClass = "static";
		    }
		}
	    }

	    $rows = $this->bug_model->bugsForSignatures(array_unique($signatures));
	    $bugzilla = new Bugzilla;
	    $signature_to_bugzilla = $bugzilla->signature2bugzilla($rows, Kohana::config('codebases.bugTrackingUrl'));

	    $this->navigationChooseVersion($product, $version);

	    if ($this->input->get('format') == "csv") {
		$this->setViewData(array('top_crashers' => $this->_csvFormatArray($resp->crashes)));
		$this->renderCSV("${product}_${version}_" . date("Y-m-d"));
	    } else {
		$this->setViewData(array(
				       'resp'         => $resp,
				       'duration_url' => url::site(implode($duration_url_path, '/') . '/'),
				       'last_updated' => $resp->end_date,
				       'other_durations' => $other_durations,
				       'percentTotal' => $resp->totalPercentage,
				       'product'      => $product,
				       'version'      => $version,
				       'sig2bugs'     => $signature_to_bugzilla,
				       'start'        => $resp->start_date,
				       'top_crashers' => $resp->crashes,
				       'total_crashes' => $resp->totalNumberOfCrashes
				       ));
	    }
	} else {
	    header("Data access error", TRUE, 500);
	    $this->setViewData(array('product'      => $product,
				     'version'      => $version,
				     'resp'         => $resp));
	}
    }

    /**
     * Copy used for NULL signatures
     */
    public static $no_sig = '(signature unavailable)';

    /**
     * AJAX request for grabbing crash history data to be plotted
     * @param string - the product
     * @param string - the version
     * @param string - the signature OR $no_sig
	 * @param string	The start date by which to begin the plot
	 * @param string	The end date by which to end the plot
     * @return responds with JSON suitable for plotting
     */
    public function plot_signature($product, $version, $signature, $start_date, $end_date)
    {
	//Bug#532434 Kohana is escaping some characters with html entity encoding for security purposes
	$signature = html_entity_decode($signature);

	header('Content-Type: text/javascript');
	$this->auto_render = FALSE;

	$config = array();
	$credentials = Kohana::config('webserviceclient.basic_auth');
	if ($credentials) {
	    $config['basic_auth'] = $credentials;
	}
	$service = new Web_Service($config);

	$host = Kohana::config('webserviceclient.socorro_hostname');

	$cache_in_minutes = Kohana::config('webserviceclient.topcrash_vers_rank_cache_minutes', 60);
	$start_date = str_replace(" ", "T", $start_date.'+0000', TimeUtil::roundOffByMinutes($cache_in_minutes));
	$end_date = str_replace(" ", "T", $end_date.'+0000', TimeUtil::roundOffByMinutes($cache_in_minutes));
	$duration = TimeUtil::determineHourDifferential($start_date, $end_date); // Number of hours

	$start_date = urlencode($start_date);
	$end_date = urlencode($end_date);

	$limit = Kohana::config('topcrashbysig.byversion_limit', 300);
	$lifetime = $cache_in_minutes * 60; // Lifetime in seconds

	$p = urlencode($product);
	$v = urlencode($version);
	
	$sig = urlencode($signature); //NPSWF32.dll%400x136a29
	$rsig = rawurlencode($signature); //NPSWF32.dll%400x136a29
	Kohana::log('info', "Turning \n$signature \n$sig \n$rsig");
	// Every 3 hours
        $resp = $service->get("${host}/200911/topcrash/sig/trend/history/p/${p}/v/${v}/sig/${rsig}/end/${end_date}/duration/${duration}/steps/60",
			      'json', $lifetime);


	if($resp) {
	    $data = array('startDate' => $resp->{'start_date'},
			  'endDate'   => $resp->{'end_date'},
			  'signature' => $resp->signature,
		          'counts'    => array(),
			  'percents'  => array());
	    for ($i =0; $i < count($resp->signatureHistory); $i++) {

		$item = $resp->signatureHistory[$i];
		array_push($data['counts'], array(strtotime($item->date) * 1000, $item->count));
		array_push($data['percents'], array(strtotime($item->date) * 1000, $item->percentOfTotal * 100));
	    }
	    echo json_encode($data);
	} else {
	    echo json_encode(array('error' => 'There was an error loading the data'));
	}
    }

   /**
    * Utility method for checking for expected properties
    * in the output of a web service call. If any are missing
    * then an alert will be logged and a default value will be set.
    * @param object - The object that is the result of a web service call
    * @param array - An assocative array where the key is a property and the value is a default
    * @param string - A useful log msg for tracking down which 
    *                 part of the results object was missing parameters
    * @void - logs on missing properties, $crash is altered when missing properties
    */
    private function _ensureProperties(&$crash, $req_props, $log_msg)
    {

	$missing_prop = FALSE;
	$missing_prop_names = array();
	foreach ($req_props as $prop => $default_value) {
	    if (! property_exists($crash, $prop)) {
		$missing_prop = TRUE;
		$crash->{$prop} = $default_value;
		array_push($missing_prop_names, $prop);
	    }
	}
	if ($missing_prop) {
	    Kohana::log('alert', "Required properites are missing from $log_msg - " . implode(', ', $missing_prop_names));
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
        $csvData = array(array('Rank', 'Change In Rank', 'Percentage of All Crashes', 
			       'Previous Percentage', 'Signature', 
			       'Total', 'Win', 'Linux', 'Mac'));
	$i = 0;
        foreach ($topcrashers as $crash) {
	    $line = array();
	    $sig = strtr($crash->signature, array(
                    ',' => ' ',
                    '\n' => ' ',
		    '"' => '&quot;'
            ));
	    array_push($line, $i);
	    array_push($line, $crash->changeInRank);
	    array_push($line, $crash->percentOfTotal);
	    array_push($line, $crash->previousPercentOfTotal);
	    array_push($line, $sig);
	    array_push($line, $crash->count);
	    array_push($line, $crash->win_count);
	    array_push($line, $crash->mac_count);
	    array_push($line, $crash->linux_count);
	    array_push($csvData, $line);
	    $i++;
	}
      return $csvData;
    }

    /**
     * Helper method for formatting a topcrashers list of objects into data 
     * suitable for CSV output
     * @param array of topCrashersBySignature object
     * @return array of strings
     * @see Topcrashers_Model
     */
    private function _csvFormatOldArray($topcrashers)
    {
        $csvData = array(array('Rank, Percentage of All Crashes, Signature, Total, Win, Linux, Mac'));
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

        $signature_to_bugzilla = array();
	$signatures = array();

	if ($last_updated !== FALSE) {
	    $start = $this->topcrashers_model->timeBeforeOffset($duration, $last_updated);
	    $totalCrashes = $this->topcrashers_model->getTotalCrashesByBranch($branch, $start, $last_updated);
	    if ($totalCrashes > 0) {
		$top_crashers = $this->topcrashers_model->getTopCrashersByBranch($branch, $limit, $start, $last_updated, $totalCrashes);
		for($i=0; $i < count($top_crashers); $i++) {
		    $percentTotal += $top_crashers[$i]->percent;
                    if ($this->input->get('format') != "csv") {
		        $top_crashers[$i]->percent = number_format($top_crashers[$i]->percent * 100, 2) . "%";
			array_push($signatures, $top_crashers[$i]->signature);
		    }
		}
		$rows = $this->bug_model->bugsForSignatures(array_unique($signatures));
		$bugzilla = new Bugzilla;
		$signature_to_bugzilla = $bugzilla->signature2bugzilla($rows, Kohana::config('codebases.bugTrackingUrl'));
	    }
	}
        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));
        if ($this->input->get('format') == "csv") {
  	    $this->setViewData(array('top_crashers' => $this->_csvFormatOldArray($top_crashers)));
  	    $this->renderCSV("${branch}_" . date("Y-m-d"));
	} else {
	    $duration_url_path = array(Router::$controller, Router::$method, $branch, "");
	    $this->setViewData(array(
                'branch'       => $branch,
		'last_updated' => $last_updated, 
		'percentTotal' => $percentTotal,
		'other_durations' => $other_durations,
	        'duration_url' => url::site(implode($duration_url_path, '/')),
		'sig2bugs' => $signature_to_bugzilla,
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
	$this->navigationChooseVersion($product, $version);
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
	$this->navigationChooseVersion($product, $version);
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
     * List the top 100 (x) Alexa top site domains, ordered by site ranking, and 
 	 * show the bugs that affect them.
     * 
	 * @access 	public
     * @param 	string 	The product name (e.g. 'Firefox')
     * @param 	string 	The version (e.g. '3.7a1pre')
 	 * @return 	void
     */
    public function bytopsite($product, $version) {
		$by_url_model = new TopcrashersByUrl_Model();
        list($start_date, $end_date, $top_crashers) = $by_url_model->getTopCrashersByTopsiteRank($product, $version);

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));

        $this->setViewData(array(
	    	'beginning' 	=> $start_date,
            'ending_on' 	=> $end_date,
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
