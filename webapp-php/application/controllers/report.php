<?php defined('SYSPATH') or die('No direct script access.');

/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Socorro Crash Reporter
 *
 * The Initial Developer of the Original Code is
 * The Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2006
 * the Initial Developer. All Rights Reserved.
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

require_once(Kohana::find_file('libraries', 'bugzilla', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'Correlation', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'crash', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'moz_pager', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'MY_SearchReportHelper', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'timeutil', TRUE, 'php'));

/**
 * List, search, and show crash reports.
 */
class Report_Controller extends Controller {

    /**
     * The default url for bug reporting; added here in case unavailable 
     * in web-app/application/config/application.php
     */
	private $report_bug_url_default = 'https://bugzilla.mozilla.org/enter_bug.cgi?';

	/**
     * Class Constructor
     */
    public function __construct()
    {
        parent::__construct();
    
        $this->crash = new Crash;
    }

    /**
     * Authentication is required.  If authenticated, return.  If not, throw a 403 error.
     *
     * @return void
     */
    private function _APIAuthenticationRequired()
    {
        $authenticated = ($this->auth_is_active && Auth::instance()->logged_in()) ? true : false;
        if ($authenticated) {
            return true;
        } else {
            header("HTTP/1.0 401 Unauthorized");
            echo json_encode(array(
               'status_code' => '401',
               'message' => 'Authenticated is required to fetch this data set.' 
            ));
            exit;
        }
    }
    
    /**
     * Throw a 404 error for an API call and exit.
     *
     * @return void
     */
    private function _APIThrow404()
    {
        header("HTTP/1.0 404 Not Found");
        echo json_encode(array(
            'error_code' => 404, 
            'message' => 'This crash report could not be found.'
        ));
        exit;
    }
    
    /**
     * Determines the crashiest product/version combo for a given set
     * of crashes. Useful for search results that may have mixed
     * products and versions
     *
     * @param array $reports Database results for top crashes which is an array 
     *              of objects
     *
     * @return array An array of strings. The product and version with the most 
     *              crashes. Example: ['Firefox', '3.6']
     */
    private function _correlationProdVers($reports)
    {
        $product_versions = array();

        $crashiest_product = '';
        $crashiest_version = '';
        $crashiest_product_version_count = 0;

        foreach ($reports as $report) {
            $key = $report->product . $report->version;
            if ( ! array_key_exists($key, $report)) {
                $product_versions[$key] = 0;
            }
            $product_versions[$key]++;
            if ($product_versions[$key] > $crashiest_product_version_count) {
                $crashiest_product = $report->product;
                $crashiest_version = $report->version;
                $crashiest_product_version_count = $product_versions[$key];
            }
        }
        return array($crashiest_product, $crashiest_version);
    }

    /**
     * Determines the crashiest Operating System for a 
     * given set of builds. Useful for search results which 
     * may contain multiple builds.
     *
     * @param array $builds Database results for builds. An array of objects
     *
     * @return string - Correlation Operating System code Example: 'Windows NT'
     */
    private function _correlations($builds)
    {
        $windows = 0;
        $mac     = 0;
        $linux   = 0;
        foreach($builds as $build) {
            $windows += $build->count_windows;
            $mac     += $build->count_mac;
            $linux   += $build->count_linux;
        }
        return Correlation::correlationOsName($windows, $mac, $linux);
    }

 	/**
     * Generate crashes by given platforms / builds
     *
	 * @access 	private
     * @param 	array 	An array of platform objects
 	 * @param	array 	An array of builds
	 * @return void
	 */
    private function _generateCrashesByBuild($platforms, $builds){
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
    private function _generateCrashesByOS($platforms, $builds){
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
     * Helper method for formatting the Hang Type
     * 
     * @param object $report
     *
     * @return string Examples: 'Plugin' or 'Browser'
     */
    private function _hangType($report)
    {
        if (property_exists($report, 'processType')) {
            return ucfirst($report->processType);
        } else {
            return 'Browser';
        }
    }

    /**
     * Helper method for determining the hang details
     * of a crash report, by gathering more data about
     * related crashes.
     *
     * This method doesn't check for hang versus non-hang
     * crash status.
     *
     * @param object $report
     * 
     * @return array with keys 'hangtype' and possibly 
     *         'other_uuid', 'pair_error', 'pair_label'
     */
    private function _makeOoppDetails($report)
    {
        $details = array();
        if (property_exists($report, 'hangid') && ! empty($report->hangid)) {
            $details['hangtype'] = $this->_hangType($report);
            $otherUuid = $this->report_model->getPairedUUID($report->hangid, $report->uuid);
	    if ($otherUuid) {
                $details['other_uuid'] = $otherUuid;
                $data_urls = $this->crash->formatDataURLs($otherUuid);
                $otherReport = $this->crash->getCrashProcessed($otherUuid);
	    } else {
		$details['pair_error'] = "Hang ID " . $report->hangid . " but no other OOID pair found";
                return $details;
	    }
            if (is_null($otherReport)) {
                $details['pair_error'] = "Unable to load <a href='$otherUuid'>$otherUuid</a> please reload this page in a few minutes";
            } else {
		$details['pair_label'] = $this->_hangType($otherReport);
            }
        }

        return $details;
    }
   
    /**
     * Display the 404 page that is custom to the pending reports page.
     * 
     * @param   string     The OOID for this report
     * @return  void
     */
    private function _OOID_404($ooid) {
        Kohana::log('alert', "The given OOID ".$ooid." could not be found.");
        return Event::run('system.404');
    }
    
    /**
     * Prepare the link by which the bug will be submitted.
     * 
     * @param   object     The $report object.
     * @return  void
     */
	private function _prepReportBugURL($report)
	{
		$report_bug_url = Kohana::config('application.report_bug_url');		
		if (empty($report_bug_url)) $report_bug_url = $this->report_bug_url_default;

		$report_bug_url .= 'advanced=1&';

		if (isset($report->product) && !empty($report->product)) {
			$report_bug_url .= 'product='.rawurlencode($report->product) . '&';
		}

		if (isset($report->os_name) && !empty($report->os_name)) {
			$report_bug_url .= 'op_sys='.rawurlencode($report->os_name) . '&';
		}

		if (isset($report->cpu_name) && !empty($report->cpu_name)) {
			$report_bug_url .= 'rep_platform='.rawurlencode($report->cpu_name) . '&';
		}
		
		$report_bug_url .= 'short_desc=' . rawurlencode('crash ');
		if (isset($report->signature) && !empty($report->signature)) {
			$report_bug_url .= rawurlencode('[@ ' . $report->signature . ']');
		}
		$report_bug_url .= '&';
		
		$report_bug_url .= 'comment='.
			rawurlencode(
				"This bug was filed from the Socorro interface and is \r\n".
				"report bp-" . $report->uuid . " .\r\n".
				"============================================================= \r\n"
			);
		
		return $report_bug_url;
	}

    /**
     * Determine and set the display signature.
     *
     * @param  array    An array of updated $_GET parameters
     * @return void
     */
    private function _setupDisplaySignature($params)
    {
        if (array_key_exists('missing_sig', $params) &&
            ! empty($params['missing_sig'])) {
            if ($params['missing_sig'] == Crash::$empty_sig_code) {
                $signature =  Crash::$empty_sig;		
            } else {
                $signature = Crash::$null_sig;		
            }
        } else if (array_key_exists('signature', $params)) {
            $signature = $params['signature'];
        } else if (
            array_key_exists('query_search', $params) &&
            $params['query_search'] == 'signature' &&
            array_key_exists('query', $params)
        ) {
            $signature = $params['query'];
        }
        if (isset($signature)) {
            $this->setViewData(array('display_signature' => $signature));
        }
    }
	
    /**
     * Validate that the OOID string submitted is a valid OOID.  If not, throw a 404 error.
     * 
     * @param   string  The OOID for this report
     * @return  string  The OOID
     */
    private function _validateOOID($ooid)
    {
        // Validate the OOID
        $ooid = $this->crash->parseOOID($ooid);
        if ($ooid == FALSE) {
            $this->_OOID_404($ooid);
        }
        if (!$this->crash->validateOOID($ooid)) {
            $this->_OOID_404($ooid);
        }
        return trim($ooid);
    }

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
        $params['admin'] = ($this->auth_is_active && Auth::instance()->logged_in()) ? true : false;

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
		$platLabels = $this->_generateCrashesByBuild($platforms, $builds); 
	    } else {
		$crashGraphLabel = "Crashes By OS";
		$platLabels = $this->_generateCrashesByOS($platforms, $builds);
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

	    list($correlation_product, $correlation_version) = $this->_correlationProdVers($reports);

            foreach ($reports as $report) {
                $hang_details = array();
                $hang_details['is_hang'] = ! empty($report->hangid);
                $hang_details['is_plugin'] = ! empty($report->plugin_id);
                $hang_details['link'] = '#';//Crash level view, linkify widgets
                $hang_details['uuid'] = $report->uuid;
                $hang_details['hangid'] = $report->hangid;
                $report->{'hang_details'} = $hang_details;
            }

        $product = (isset($product) && !empty($product)) ? $product : Kohana::config('products.default_product');
	    $this->setViewData(array(
		'navPathPrefix' => $currentPath,
		'nextLinkText' => 'Older Crashes',
		'pager' => $pager,
		'params'  => $params,
		'previousLinkText' => 'Newer Crashes',
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
		'correlation_product' => $correlation_product,
		'correlation_version' => $correlation_version,
		'correlation_os' => $this->_correlations($builds),
		'logged_in' => $logged_in,
        'url_base' => url::site('products/'.$product),
		'url_nav' => url::site('products/'.$product),        
	    ));
	}
    }
    
    /**
     * Ajax method for getting related crash
     *
     * @param string $uuid
     *
     * @return string JSON formatted list of crash reports
     */
    public function hang_pairs($uuid)
    {
        $this->auto_render = false;

        $rs = $this->report_model->getAllPairedUUIDByUUid($uuid);
        $crashes = array();
        foreach ($rs as $row) {
            $report = $this->crash->getCrashProcessed($row->uuid);
            if ($report && property_exists($report, 'date_processed' )) {
                $d = strtotime($report->{'date_processed'});
                $report->{'display_date_processed'} = date('M d, Y H:i', $d);
                array_push($crashes, $report);
	    }
        }
        echo json_encode($crashes);
        exit;
    }

    /**
     * Fetch and display a single report.
     *
     * Note: Correlation tab is populated via /correlation/ajax/cpu/{product}/{version}/{os_name}/{signature}/
     * 
     * @param 	string 	The ooid
     * @return 	void
     */
    public function index($ooid) {
        if ($ooid = $this->_validateOOID($ooid)) {
            $report = $this->crash->getCrashProcessed($ooid);
            if (isset($report->status_code) && $report->status_code == 200) {
                $logged_in = $this->auth_is_active && Auth::instance()->logged_in();
                if ($logged_in) {
                    $this->sensitivePageHTTPSorRedirectAndDie('/report/index/' . $ooid);
                }
                
                $comments = array();
                $signature_to_bugzilla = array();
                $report = $this->crash->prepareCrashReport($report);
                cachecontrol::set(array(
                    'etag'          => $ooid,
                    'last-modified' => strtotime($report->date_processed)
                ));
                
                $bug_model = new Bug_Model;
                $bugzilla = new Bugzilla;
                $Extension_Model = new Extension_Model;
                
                $rows = $bug_model->bugsForSignatures(array($report->signature));
                $comments = $this->common_model->getCommentsBySignature($report->signature);
                $data_urls = $this->crash->formatDataURLs($ooid);
                $extensions = $Extension_Model->getExtensionsForReport($ooid, $report->date_processed, $report->product);
                $ooppDetails = $this->_makeOoppDetails($report);        
                $product = (isset($report->product) && !empty($report->product)) ? $report->product : Kohana::config('products.default_product');
                $signature_to_bugzilla = $bugzilla->signature2bugzilla($rows, Kohana::config('codebases.bugTrackingUrl'));
                
                $this->setViewData(array(
                    'branch' => $this->branch_model->getByProductVersion($report->product, $report->version),
                    'comments' => $comments,
                    'extensions' => $extensions,
                    'logged_in' => $logged_in,
		        	'data_urls' => $data_urls,
                    'report' => $report,
                    'report_bug_url' => $this->_prepReportBugURL($report), 
                    'sig2bugs' => $signature_to_bugzilla,
                    'url_nav' => url::site('products/'.$product),
                    'oopp_details' => $ooppDetails,
                    'url_base' => url::site('products/'.$product),
                    'url_nav' => url::site('products/'.$product),
                ));
            } else {
                if (isset($report->status_code) && $report->status_code == 200) {
                    return url::redirect('report/pending/'.$ooid);
                } else {
                    $this->_OOID_404($ooid);
                }
            }
        }
    }

    /**
     * Fetch the meta data for a crash report and return this data in JSON.
     *
     * @bizrule Authentication is required for this call.
     * @param 	string 	The ooid
     * @return 	void
     */
    public function meta($ooid) {
        $this->_APIAuthenticationRequired();
        if ($ooid = $this->crash->parseOOID($ooid)) {
            $report = $this->crash->getCrashMeta($ooid);
            if (isset($report->status_code) && $report->status_code == 200) {
                header("Content-Type: text/plain; charset=UTF-8");
                echo trim(json_encode($report)); 
                exit;
            } else {
                // @todo update this to use the appropriate status code
                $this->_throw404();
            }
        } else {
            // @todo update this to use this appropriate status code
            $this->_APIThrow404();
        }
    }

    /**
     * Wait while a pending job is processed.
     * 
     * @access  public
     * @param   string     The OOID for this report
     * @return  void
     */
    public function pending($ooid) {
        if ($ooid = $this->_validateOOID($ooid)) {
            $report = $this->crash->getCrashProcessed($ooid);
            if (isset($report->status_code) && $report->status_code == 200) {
                return url::redirect('report/index/'.$ooid);            
            }
            
            $product = (isset($product) && !empty($product)) ? $product : Kohana::config('products.default_product');
            $this->setViewData(array(
                'ooid' => $ooid,
                'uuid' => $ooid,
		    	'status' => null,
		    	'url_ajax' => url::site() . 'report/pending_ajax/' . $ooid,
                'url_base' => url::site('products/'.$product),			
                'url_nav' => url::site('products/'.$product),			
            ));
        }
    }
    
  /**
   * Determine whether or not pending report has been found yet.  If so,
   * redirect the user to that url.
   *
   * @access   public
   * @param    string  The $ooid for this report
   * @return   string  Return the url to which the user should be redirected.
   */
    public function pending_ajax ($ooid)
    {
        if ($ooid = $this->_validateOOID($ooid)) {
            $status = array();
            
            // Check for the report
            $report = $this->crash->getCrashProcessed($ooid);
            if (isset($report->status_code) && $report->status_code == 200) {
    	        $status['status'] = 'ready';
    	        $status['status_message'] = 'The report for ' . $ooid . ' is now available.';
    	        $status['url_redirect'] = url::site('report/index/'.$ooid);
            } else {
                $status['status'] = 'error';
                $status['status_message'] = 'The report for ' . $ooid . ' is not available yet.';
                $status['url_redirect'] = '';
            }
            
            echo json_encode($status);
            exit;
        }
    }
    
    /**
     * Fetch and display a json dump of the processed crash report.
     *
     * @param 	string 	The ooid
     * @return 	void
     */
    public function processed($ooid) {
        if ($ooid = $this->crash->parseOOID($ooid)) {
            $report = $this->crash->getCrashProcessed($ooid);
            if (isset($report->status_code) && $report->status_code == 200) {
                header("Content-Type: text/plain; charset=UTF-8");
                echo trim(json_encode($report)); 
                exit;
            } else {
                // @todo update this to use this appropriate status code
                $this->_APIThrow404();
            }
        } else {
            // @todo update this to use this appropriate status code
            $this->_APIThrow404();
        }
    }
    
    /**
     * Fetch and display the raw crash dump.
     *
     * @bizrule Authentication is required.
     * @param 	string 	The ooid
     * @return 	void
     */
    public function raw_crash($ooid) {
        $this->_APIAuthenticationRequired();
        if ($ooid = $this->crash->parseOOID($ooid)) {
            $report = $this->crash->getCrashRawCrash($ooid);
            if (!empty($report)) {
                header("Content-Type: text/plain; charset=UTF-8");
                echo trim($report);
                exit;
            } else {
                // @todo update this to use this appropriate status code
                $this->_APIThrow404();
            }
        }

        // @todo update this to use this appropriate status code
        $this->_APIThrow404();
    }

}