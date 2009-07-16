<?php defined('SYSPATH') or die('No direct script access.');

require_once(Kohana::find_file('libraries', 'bugzilla', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'crash', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'MY_SearchReportHelper', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'MY_QueryFormHelper', TRUE, 'php'));

/**
 *
 */
class Query_Controller extends Controller {

    public function __construct()
    {
        parent::__construct();
	$this->bug_model = new Bug_Model;
    }

    /**
     *
     */
    public function query() {
      //Query Form Stuff
        $searchHelper = new SearchReportHelper;
        $queryFormHelper = new QueryFormHelper;

	$queryFormData = $queryFormHelper->prepareCommonViewData($this->branch_model, $this->platform_model);
	$this->setViewData($queryFormData);

	//Current Query Stuff
        $params = $this->getRequestParameters($searchHelper->defaultParams());
        $searchHelper->normalizeParams( $params );

	$this->_updateNavigation($params);

        $signature_to_bugzilla = array();

        cachecontrol::set(array(
            'etag'     => $params,
            'expires'  => time() + ( 60 * 60 )
	    ));


        if ($params['do_query'] !== FALSE) {
            $reports = $this->common_model->queryTopSignatures($params);
            $signatures = array();
            foreach ($reports as $report) {
	          array_push($signatures, $report->signature);
	    }
            $rows = $this->bug_model->bugsForSignatures(array_unique($signatures));
	    $bugzilla = new Bugzilla;
	    $signature_to_bugzilla = $bugzilla->signature2bugzilla($rows, Kohana::config('codebases.bugTrackingUrl'));
	      
        } else {
            $reports = array();

        }

	//common getParams
	//prepareAndSetCommonViewData($params)

        // TODO: redirect if there's one resulting report signature group


        $this->setViewData(array(
            'params'  => $params,
            'queryTooBroad' => $searchHelper->shouldShowWarning(),
            'reports' => $reports,
            'sig2bugs' => $signature_to_bugzilla
	 ));
    }

    private function _updateNavigation($params)
    {
        if (array_key_exists('version', $params) &&
  	    is_array($params['version']) && 
	    count($params['version']) > 0 &&
	    substr_count($params['version'][0], ':') == 1) {
	        $parts = explode(':', $params['version'][0]);
		$this->navigationChooseVersion(trim($parts[0]), trim($parts[1]));
	} else {
	    Kohana::log('debug', "No version in params...skipping");
	}
    }

    public function simple()
    {
        $searchHelper = new SearchReportHelper;
        $params = $this->getRequestParameters(array('q' => ''));
	$q = trim($params['q']);
	if (empty($q)) {
	    //TODO error
	  } else {
	      $crash = new Crash();
              $uuid = $crash->parseUUID($q);
	      if ($uuid !== FALSE) {
                  return url::redirect('report/index/' . $uuid);
	      } else {
		  $reportDb = new Report_Model;
		  $query_type = 'startswith';
		  if ($reportDb->sig_exists($q) === TRUE) {
  		      $query_type = 'exact';
		  }

		  $this->ensureChosenVersion(array());

		  $product = urlencode($this->chosen_version['product']);
		  $version = urlencode($this->chosen_version['product'] . ':' . $this->chosen_version['version']);
		  $encq    = urlencode($q);
		  $query = "query/query?do_query=1&product=${product}&version=${version}&query_search=signature&query_type=${query_type}&query=${encq}";

                  return url::redirect($query);
	      }
	  }
    }
}
