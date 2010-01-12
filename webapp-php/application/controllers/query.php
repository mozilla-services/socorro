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
 * Contributor(s):
 *   Austin King <aking@mozilla.com>
 *   Ryan Snyder <rsnyder@mozilla.com>
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
require_once(Kohana::find_file('libraries', 'crash', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'MY_SearchReportHelper', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'MY_QueryFormHelper', TRUE, 'php'));

/**
 * The controller for simple and advanced search queries.
 */
class Query_Controller extends Controller {

    /**
     * Class constructor.
     *
     * @return void
     */
    public function __construct()
    {
        parent::__construct();
	    $this->bug_model = new Bug_Model;
    }

    /**
     * Perform the advanced search query and display the search results.
     *
     * @return void
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
		    if (is_null($report->signature)) {
			$report->{'display_signature'} = Crash::$null_sig;
			$report->{'display_null_sig_help'} = TRUE;
		        $report->{'missing_sig_param'} = Crash::$null_sig_code;
		    } else if(empty($report->signature)) {
			$report->{'display_signature'} = Crash::$empty_sig;
			$report->{'display_null_sig_help'} = TRUE;
		        $report->{'missing_sig_param'} = Crash::$empty_sig_code;
		    } else {
			$report->{'display_signature'} = $report->signature;
			$report->{'display_null_sig_help'} = FALSE;
		    }		
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

    /**
     * Update the site navigation with the request parameters.
     *
     * @return void
     */
    private function _updateNavigation($params)
    {
        if (array_key_exists('version', $params) &&
  	    is_array($params['version']) && 
	    count($params['version']) > 0 &&
	    substr_count($params['version'][0], ':') == 1) {
	        $parts = explode(':', $params['version'][0]);
		$this->navigationChooseVersion(trim($parts[0]), trim($parts[1]));
	} else {
	    Kohana::log('debug', "updateNavigation No version in params...skipping");
	}
    }

    /**
     * Perform a simple query.
     *
     * @return void
     */
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
