<?php

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
        $params['admin'] = $this->logged_in;

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
        $items_per_page = Kohana::config('search.number_report_list');

        $serviceResult = $this->report_model->crashesList($params, $items_per_page, ( $page - 1 ) * $items_per_page);
        $totalCount = $serviceResult->total;
        $reports = $serviceResult->hits;
        $pager = new MozPager($items_per_page, $totalCount, $page);

        // Code for $secureUrl should stay in sync with code for $currentPath above
        $currentPath = url::site('report/list') . '?' . html::query_string($params) . '&page=';

        if ($this->logged_in) {
            $this->sensitivePageHTTPSorRedirectAndDie($currentPath . $page);
        }

        $builds  = $this->common_model->queryFrequency($params);

        if (count($builds) > 1){
            $crashGraphLabel = "Crashes By Build Date";
            $platLabels = $this->generateCrashesByBuild($platforms, $builds);
        } else {
            $crashGraphLabel = "Crashes By OS";
            $platLabels = $this->generateCrashesByOS($platforms, $builds);
        }

        $buildTicks = array();
        $index = 0;
        for($i = count($builds) - 1; $i  >= 0 ; $i = $i - 1) {
            $buildTicks[] = array($index, gmdate('m/d', strtotime($builds[$i]->build_date)));
            $index += 1;
        }
        $bug_model = new Bug_Model;
        $signature_to_bugzilla = $bug_model->bugsForSignatures(
                                     array($params['signature']),
                                     Kohana::config('codebases.bugTrackingUrl')
                                 );

        list($correlation_product, $correlation_version) = $this->_correlationProdVers($reports);

        foreach ($reports as $report) {
            $hang_details = array();
            $hang_details['is_hang'] = ! empty($report->hangid);
            $hang_details['is_plugin'] = ! empty($report->plugin_id);
            $hang_details['is_content'] = $report->process_type == "content";
            $hang_details['link'] = '#';//Crash level view, linkify widgets
            $hang_details['uuid'] = $report->uuid;
            $hang_details['hangid'] = $report->hangid;
            $report->{'hang_details'} = $hang_details;
        }

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
            'logged_in' => $this->logged_in,
        ));
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
     * Prepare the link by which the bug will be submitted.
     *
     * @param   object     The $report object.
     * @return  void
     */
    private function _prepReportBugURL($report)
    {
        $report_bug_url = Kohana::config('application.report_bug_url');

        if (empty($report_bug_url)) {
          $report_bug_url = $this->report_bug_url_default;
        }

        $report_bug_url .= 'advanced=1&bug_severity=critical&keywords=crash&';

        if (isset($report->product) && !empty($report->product)) {
            if($report->product == 'FennecAndroid') {
                $rp = 'Fennec Native';
            } else {
                $rp = $report->product;
            }
            $report_bug_url .= 'product='.rawurlencode($rp) . '&';
        }

        if (isset($report->os_name) && !empty($report->os_name)) {
            $report_bug_url .= 'op_sys='.rawurlencode($report->os_name) . '&';
        }

        if (isset($report->cpu_name) && !empty($report->cpu_name)) {
            $report_bug_url .= 'rep_platform='.rawurlencode($report->cpu_name) . '&';
        }

        if (isset($report->signature) && !empty($report->signature)) {
            $report_bug_url .= '&cf_crash_signature=';
            $report_bug_url .= rawurlencode('[@ ' . $report->signature . ']') . '&';

            preg_match('/[A-Za-z0-9_:@]+/' , $report->signature, $matches, PREG_OFFSET_CAPTURE);
            $report_bug_url .= 'short_desc=' . rawurlencode('crash ' . $matches[0][0]) . '&';
        }

        $report_bug_url .= '&comment=' . rawurlencode(
            "This bug was filed from the Socorro interface and is \r\n".
            "report bp-" . $report->uuid . " .\r\n".
            "============================================================= \r\n"
        );

        return $report_bug_url;
    }

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
        $uuid = $crash->parseOOID($id);

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
     * Note: Correlation tab is populated via /correlation/ajax/cpu/{product}/{version}/{os_name}/{signature}/
     *
     * @param 	string 	The uuid
     * @return 	void
     */
    public function index($id = null) {
        $crash = new Crash();
        $uuid = $crash->parseOOID($id);
        if ($uuid == FALSE ) {
            return Event::run('system.404');
        }

	$reportJsonZUri = sprintf(Kohana::config('application.crash_dump_public_url'), $uuid);
	$raw_dump_urls = $this->report_model->formatRawDumpURLs($uuid);

	$report = $this->fetchUUID($uuid);

        if ( is_bool($report) && $report == true) {
	        return url::redirect('report/pending/'.$uuid);
        } else if ( (is_bool($report) && $report == false) || is_null($report) ) {
            $this->setView('report/notfound');
            $this->setViewData(
                array(
                    'base_url' => url::site('products'),
                    'products'  => $this->current_products,
                    'nav_selection' => null,
                )
            );
            return;
	} else {
	    if ($this->logged_in) {
		$this->sensitivePageHTTPSorRedirectAndDie('/report/index/' . $id);
	    }

            cachecontrol::set(array(
                'etag'          => $uuid,
                'last-modified' => strtotime($report->date_processed)
            ));

	    $comments = array();
	    $signature_to_bugzilla = array();

        // If the signature is NULL in the DB, we will have an empty raw dump
	    // We can't trust signature, it is empty string for both NULL and Empty String
	    // To make it easy for pages that don't handel missing or NULL signatures
	    if (strlen($report->dump) <= 1) {
		$report->{'display_signature'} = Crash::$null_sig;
	    } else if (empty($report->signature)) {
		$report->{'display_signature'} = Crash::$empty_sig;
	    } else {
		$report->{'display_signature'} = $report->signature;
		$report->sumo_signature = $this->_makeSumoSignature($report->signature);
		$bug_model = new Bug_Model;
	    	$signature_to_bugzilla = $bug_model->bugsForSignatures(
                                             array($report->signature),
                                             Kohana::config('codebases.bugTrackingUrl')
                                         );
                $comments = $this->common_model->getCommentsBySignature($report->signature);
	    }

            $Extension_Model = new Extension_Model;
            $extensions = $Extension_Model->getExtensionsForReport($uuid, $report->date_processed, $report->product);

            $ooppDetails = $this->_makeOoppDetails($report);

            $product = (isset($report->product) && !empty($report->product)) ? $report->product : Kohana::config('products.default_product');
		$this->setViewData(array(
        	    'branch' => $this->branch_model->getByProductVersion($report->product, $report->version),
        	    'comments' => $comments,
        	    'extensions' => $extensions,
        	    'logged_in' => $this->logged_in,
				'raw_dump_urls' => $raw_dump_urls,
        	    'reportJsonZUri' => $reportJsonZUri,
        	    'report' => $report,
        	    'report_bug_url' => $this->_prepReportBugURL($report),
        	    'sig2bugs' => $signature_to_bugzilla,
                    'url_nav' => url::site('products/'.$product),
                    'oopp_details' => $ooppDetails,
        	));
	}
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
                $crash_uri = sprintf(Kohana::config('application.crash_dump_local_url'), $otherUuid);
                $reportJsonZUri = sprintf(Kohana::config('application.crash_dump_public_url'), $otherUuid);
                $raw_dump_urls = $this->report_model->formatRawDumpURLs($otherUuid);

                $otherReport = $this->fetchUUID($otherUuid);
	    } else {
		$details['pair_error'] = "Hang ID " . $report->hangid . " but no other UUID pair found";
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
     * Wait while a pending job is processed.
     *
     * @access  public
     * @param   int     The UUID for this report
     * @return  void
     */
    public function pending($id) {
        $crash = new Crash();
	$status = null;
        $uuid = $crash->parseOOID($id);
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
        $report = $this->fetchUUID($uuid);

        if (! is_null($report) && ! is_bool($report)) {
	    return url::redirect('report/index/'.$uuid);
	}

        // Fetch Job
        $this->job_model = new Job_Model();
        $job = $this->job_model->getByUUID($uuid);

        $product = (isset($product) && !empty($product)) ? $product : Kohana::config('products.default_product');
        $this->setViewData(array(
            'uuid' => $uuid,
            'job'  => $job,
			'status' => $status,
			'url_ajax' => url::site() . 'report/pending_ajax/' . $uuid,
            'url_nav' => url::site('products/'.$product),
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
        $report = $this->fetchUUID($uuid);

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
     * Ajax method for getting related crash
     *
     * @param string $uuid
     *
     * @return string JSON formatted list of crash reports
     */
    public function hang_pairs($uuid=null)
    {
        if(is_null($uuid)) {
            Kohana::show_404();
        }
        $this->auto_render = false;

        $rs = $this->report_model->getAllPairedUUIDByUUid($uuid);
        $crashes = array();
        foreach ($rs as $row) {
            $crash_uri = sprintf(Kohana::config('application.crash_dump_local_url'), $row->uuid);
            $report = $this->fetchUUID($row->uuid);
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

    /**
     * Attempt to fetch the processed report (jsonz), optionally
     * falling back.
     *
     * @uuid    string  The UUID to look up 
     */
    protected function fetchUUID($uuid) {
        $crash_uri = sprintf(Kohana::config('application.crash_dump_local_url'), $uuid);
        $crash_uri_fallback = sprintf(Kohana::config('application.crash_dump_local_url_fallback'), $uuid);

        $report = $this->report_model->getByUUID($uuid, $crash_uri);
        if (empty($report) && !empty($crash_uri_fallback)) {
            $report = $this->report_model->getByUUID($uuid, $crash_uri_fallback);
        }

        return $report;
    }
}
