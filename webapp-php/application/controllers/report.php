<?php
require_once(Kohana::find_file('libraries', 'bugzilla', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'crash', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'moz_pager', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'MY_SearchReportHelper', TRUE, 'php'));

/**
 * List, search, and show crash reports.
 */
class Report_Controller extends Controller {

    /**
     * List reports for the given search query parameters.
	 * 
	 * @access	public
	 * @return 	void
     */
    public function do_list() {
        $helper = new SearchReportHelper();

        $branch_data = $this->branch_model->getBranchData();
        $platforms   = $this->platform_model->getAll();

	$d = $helper->defaultParams();
	// params allowed in the query string
	$d['signature'] = '';
	$d['missing_sig'] = '';

        $params = $this->getRequestParameters($d);

        $helper->normalizeParams( $params );
        $this->_setupDisplaySignature($params);

        cachecontrol::set(array(
            'etag'     => $params,
            'expires'  => time() + ( 60 * 60 )
        ));
	$input = new Input;
        $page = $input->get('page');

	if ($page === NULL) {
	    $page = 1;
	}
        $totalCount = $this->common_model->totalNumberReports($params);
        $pager = new MozPager(Kohana::config('search.number_report_list'), $totalCount, $page);

        $reports = $this->common_model->queryReports($params, $pager);

        if (count($reports) == 0) {
            header("No data for this query", TRUE, 404);
	    $this->setView('common/nodata');
	} else {
	    // Code for $secureUrl should stay in sync with code for $currentPath above
	    $currentPath = url::site('report/list') . '?' . html::query_string($params) . '&page=';
	    
            $logged_in = $this->auth_is_active && Auth::instance()->logged_in();
	    if ($logged_in) {
		$this->sensitivePageHTTPSorRedirectAndDie($currentPath . $page);
	    }

	    $builds  = $this->common_model->queryFrequency($params);
	    
	    if (count($builds) > 1){
		$crashGraphLabel = "Crashes By Build";
		$platLabels = $this->generateCrashesByBuild($platforms, $builds); 
	    } else {
		$crashGraphLabel = "Crashes By OS";
		$platLabels = $this->generateCrashesByOS($platforms, $builds);
	    }
        	
	    $buildTicks = array();
	    $index = 0;
	    for($i = count($builds) - 1; $i  >= 0 ; $i = $i - 1) {
		$buildTicks[] = array($index, date('m/d', strtotime($builds[$i]->build_date)));
		$index += 1;
	    }
	    $bug_model = new Bug_Model;
	    $rows = $bug_model->bugsForSignatures(array($params['signature']));
	    $bugzilla = new Bugzilla;
	    $signature_to_bugzilla = $bugzilla->signature2bugzilla($rows, Kohana::config('codebases.bugTrackingUrl'));
        	
	    $this->setViewData(array(
		'navPathPrefix' => $currentPath,
		'nextLinkText' => 'Older Crashes',
		'pager' => $pager,
		'params'  => $params,
		'previousLinkText' => 'Newer Crashes',
		'queryTooBroad' => $helper->shouldShowWarning(),
		'reports' => $reports,
		'totalItemText' => " Crash Reports",

        	
		'all_products'  => $branch_data['products'],
		'all_branches'  => $branch_data['branches'],
		'all_versions'  => $branch_data['versions'],
		'all_platforms' => $platforms,

		'builds'  => $builds,        	
		'buildTicks'      => $buildTicks,
		'crashGraphLabel' => $crashGraphLabel,
		'platformLabels'  => $platLabels,
        	
		'sig2bugs' => $signature_to_bugzilla,
		'comments' => $this->common_model->getCommentsByParams($params),
		'logged_in' => $logged_in,
	    ));
	}
    }
    private function _setupDisplaySignature($params)
    {
	if (array_key_exists('missing_sig', $params) &&
	    ! empty($params['missing_sig'])) {
	    if ($params['missing_sig'] == Crash::$empty_sig_code) {
		$signature = Crash::$null_sig;		
	    } else {
		$signature =  Crash::$empty_sig;		
	    }
	} else if (array_key_exists('signature', $params)) {
	    $signature = $params['signature'];
	} else if (array_key_exists('query_search', $params) &&
		   $params['query_search'] == 'signature' &&
	           array_key_exists('query', $params)) {
	    $signature = $params['query'];
	}
	if (isset($signature)) {
	    $this->setViewData(array('display_signature' => $signature));
	}

    }

    /**
     * Linking reports with ID validation.
     *
     * This method should not touch the database!
     */
    public function find() {
        $crash = new Crash();
        $id = isset($_GET['id']) ? $_GET['id'] : '';
        $uuid = $crash->parseUUID($id);

        if ($uuid) {
            return url::redirect('report/index/'.$uuid);
        } else {
            return url::redirect('');
        }
    }

   	/**
     * Generate crashes by given platforms / builds
     *
	 * @access 	private
     * @param 	array 	An array of platform objects
 	 * @param	array 	An array of builds
	 * @return void
	 */
    private function generateCrashesByBuild($platforms, $builds){
		$platLabels = array();
		foreach ($platforms as $platform){
			$plotData = array();
			$index = 0;
			for($i = count($builds) - 1; $i  >= 0; $i = $i - 1){
	  			$plotData[] = array($index, $builds[$i]->{"count_$platform->id"});
          		$index += 1;
			}
			$platLabels[] = array(
				"label" => substr($platform->name, 0, 3),
				"data"  => $plotData,
				"color" => $platform->color
			);
		}
      	return $platLabels;
    }

    /**
     * Generate crashes by the OS
	 * 
     * @param 	array 	An array of platform objects
 	 * @param	array 	An array of builds
	 * @return 	void
     */
    private function generateCrashesByOS($platforms, $builds){
        $platLabels = array();
        $plotData =   array();
	
        for($i = 0; $i < count($platforms); $i += 1){
			$platform = $platforms[$i];
			$plotData[$platform->id] = array($i, 0);
			for($j = 0; $j  < count($builds); $j = $j + 1){ 
				$plotData[$platform->id][1] += intval($builds[$j]->{"count_$platform->id"});
			}
			$platLabels[] = array(
				"label" => substr($platform->name, 0, 3),
				"data" => array($plotData[$platform->id]),
            	"color" => $platform->color
			);
        }
		return $platLabels;
    }

    /**
     * Fetch and display a single report.
     * 
     * @param 	string 	The uuid
     * @return 	void
     */
    public function index($id) {
        $crash = new Crash();
        $uuid = $crash->parseUUID($id);
        if ($uuid == FALSE ) {
            return Event::run('system.404');
        }

	$crash_uri = sprintf(Kohana::config('application.crash_dump_local_url'), $uuid);
	$reportJsonZUri = sprintf(Kohana::config('application.crash_dump_public_url'), $uuid);
	$raw_dump_urls = $this->report_model->formatRawDumpURLs($uuid);

	$report = $this->report_model->getByUUID($uuid, $crash_uri);

        if ( is_null($report)) {
            if (!isset($_GET['p'])) {
                $this->priorityjob_model = new Priorityjobs_Model();
                $this->priorityjob_model->add($uuid);
            }
	    return url::redirect('report/pending/'.$uuid);
        } else {
            $logged_in = $this->auth_is_active && Auth::instance()->logged_in();
	    if ($logged_in) {
		$this->sensitivePageHTTPSorRedirectAndDie('/report/index/' . $id);
	    }

            cachecontrol::set(array(
                'etag'          => $uuid,
                'last-modified' => strtotime($report->date_processed)
            ));

	    $comments = array();
	    $signature_to_bugzilla = array();

	    if (is_null($report->signature)) {
		$report->{'display_signature'} = Crash::$null_sig;
	    } else if (empty($report->signature)) {
		$report->{'display_signature'} = Crash::$empty_sig;
	    } else {
		$report->{'display_signature'} = $report->signature;
		$report->sumo_signature = $this->_makeSumoSignature($report->signature);
		$bug_model = new Bug_Model;
		$rows = $bug_model->bugsForSignatures(array($report->signature));
	    	$bugzilla = new Bugzilla;
	    	$signature_to_bugzilla = $bugzilla->signature2bugzilla($rows, Kohana::config('codebases.bugTrackingUrl'));
                $comments = $this->common_model->getCommentsBySignature($report->signature);
	    }	    	
        	
	    	$Extension_Model = new Extension_Model;
	    	$extensions = $Extension_Model->getExtensionsForReport($uuid, $report->date_processed, $report->product);
	    	
			$this->setViewData(array(
        	    'branch' => $this->branch_model->getByProductVersion($report->product, $report->version),
        	    'comments' => $comments,
        	    'extensions' => $extensions,
        	    'logged_in' => $logged_in,
				'raw_dump_urls' => $raw_dump_urls,
        	    'reportJsonZUri' => $reportJsonZUri,
        	    'report' => $report,
        	    'sig2bugs' => $signature_to_bugzilla
        	));
		}
    }

    /**
     * Wait while a pending job is processed.
     * 
     * @access  public
     * @param   int     The UUID for this report
     * @return  void
     */
    public function pending($id) {
        $crash = new Crash();
	$status = null;
        $uuid = $crash->parseUUID($id);
        if ($uuid == FALSE) {
            Kohana::log('alert', "Improper UUID format for $uuid doing 404");
            return Event::run('system.404');
        }
        
        // If the YYMMDD date on the end of the $uuid string is over 3 years ago, fail.
        if (!$this->report_model->isReportValid($id)) {
            Kohana::log('alert', "UUID indicates report for $id is greater than 3 years of age.");
            header("HTTP/1.0 410 Gone"); 
			$status = intval(410);
        }        

        // Check for the report
	$crash_uri = sprintf(Kohana::config('application.crash_dump_local_url'), $uuid);
	$report = $this->report_model->getByUUID($uuid, $crash_uri);

        if (! is_null($report)) {
	    return url::redirect('report/index/'.$uuid);
	}

        // Fetch Job 
        $this->job_model = new Job_Model();
        $job = $this->job_model->getByUUID($uuid);

        $this->setViewData(array(
            'uuid' => $uuid,
            'job'  => $job,
			'status' => $status,
			'url_ajax' => url::site() . 'report/pending_ajax/' . $uuid 
        ));
    }

  /**
   * Determine whether or not pending report has been found yet.  If so,
   * redirect the user to that url.
   *
   * @access   public
   * @param    string  The $uuid for this report
   * @return   string  Return the url to which the user should be redirected.
   */
    public function pending_ajax ($uuid)
    {
	$status = array();
        // Check for the report
	$crash_uri = sprintf(Kohana::config('application.crash_dump_local_url'), $uuid);
	$report = $this->report_model->getByUUID($uuid, $crash_uri);

        if (! is_null($report)) {
	    $status['status'] = 'ready';
	    $status['status_message'] = 'The report for ' . $uuid . ' is now available.';
	    $status['url_redirect'] = url::site('report/index/'.$uuid);
	} else {
	    $status['status'] = 'error';
	    $status['status_message'] = 'The report for ' . $uuid . ' is not available yet.';
	    $status['url_redirect'] = '';
	}
	echo json_encode($status);
	exit;
    }


    /**
    * Create the Sumo signature for this report.
    *
    * @access   private
    * @param    string  The $signature
    * @return   string  The new signature
    */
    private function _makeSumoSignature($signature) {
        $memory_addr = strpos($signature, '@');
        if ($memory_addr === FALSE) {
	    return $signature;
        } else {
	    return substr($signature, 0, $memory_addr);
        }
    }
}
