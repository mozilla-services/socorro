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
        $this->queryFormHelper = new QueryFormHelper;
        $this->searchReportHelper = new SearchReportHelper;
    }

    /**
     * Prepare the reports for display.
     *
     * @param   array An array of report objects
     * @return  array An updated array of report objects
     */
    private function _prepareReports($reports)
    {
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

            $hang_details = array();
            $hang_details['is_hang'] = $report->numhang > 0;
            $hang_details['is_plugin'] = $report->numplugin > 0;
            $report->{'hang_details'} = $hang_details;
        }
        return $reports;
    }

    /**
     * Prepare the array used for report meta data.
     *
     * @return  array An array that is ready to accept report meta data.
     */

    private function _prepareReportsMetaArray()
    {
        return array(
            'showPluginFilename' => false,
            'showPluginName' => false,
            'signatures' => array()
        );
    }

    /**
     * Prepare the meta data surrounding the report, including signatures 
     * and plugin names.
     *
     * @param   array An array of report objects
     * @return  array An array of report meta data.
     */
    private function _prepareReportsMeta($reports) 
    {
        $meta = $this->_prepareReportsMetaArray();
        foreach ($reports as $report) {
            if (
                property_exists($report, 'pluginname') && ! empty($report->pluginname) ||
                property_exists($report, 'pluginversion') && ! empty($report->pluginversion)
            ) {
                $meta['showPluginName'] = true;
            }

            if (property_exists($report, 'pluginfilename') && ! empty($report->pluginfilename)) {
                $meta['showPluginFilename'] = true;
            }

            if (isset($report->signature) && !empty($report->signature)) {
                array_push($meta['signatures'], $report->signature);
            }
        }

        array_unique($meta['signatures']);
        return $meta;
    }

    /**
     * Handle a quick search query for either a UUID or stack signature.
     *
     * @param  array    An array of _GET parameters
     * @return array    An array of updated _GET parameters
     */
    public function _simple($params)
    {
        if (!empty($params['query'])) {
            $crash = new Crash();
            $uuid = $crash->parseUUID($params['query']);
            
            if ($uuid !== FALSE) {
                return url::redirect('report/index/' . $uuid);
            } else {
                $params['query_search'] = 'signature';
                $params['query_type'] = 'exact';
                $params['range_value'] = 1;
                $params['range_unit'] = 'weeks';
            }
        }
        return $params;
    }

    /**
     * Update search parameters as needed.
     *
     * @param  array    An array of _GET parameters
     * @return array    An array of updated _GET parameters
     */
    public function _updateRequestParameters($params)
    {
        // If no product is specified, add the user's last selected product
        if (!isset($_GET['product']) || !isset($params['product']) || empty($params['product'])) {
            $params['product'] = array( 0 => $this->chosen_version['product'] );
        }

        // If no version is specified, add the user's last selected product
        if (
            empty($params['version']) &&
            $params['product'][0] == $this->chosen_version['product'] &&
            !empty($this->chosen_version['version']) 
        ) {
            $product_version = $this->chosen_version['product'].":".$this->chosen_version['version'];
            $params['version'] = array( 0 => $product_version);
        } 

        // If no date is specified, add today's date.
        if (empty($params['date'])) {
            $params['date'] = date('m/d/Y H:i:s');
        }
        
        // Hang type 
        if (!isset($params['hang_type'])) {
            $params['hang_type'] = 'any';
        }
        
        // Process type
        if (!isset($params['process_type'])) {
            $params['process_type'] = 'any';
        }
        
        // Admin
        $params['admin'] = ($this->auth_is_active && Auth::instance()->logged_in()) ? true : false;
        
        // Normalize parameters
        $this->searchReportHelper->normalizeParams($params);
        
        return $params;
    }

    /**
     * Perform the advanced search query and display the search results.
     *
     * @return void
     */
    public function query() {

        $params = $this->getRequestParameters($this->searchReportHelper->defaultParams());
        $params = $this->_updateRequestParameters($params);

        // Handle simple queries.  Determine if searching for UUID or Signature.
        if (isset($_GET['query_type']) && $_GET['query_type'] == 'simple') {
            $params = $this->_simple($params);
        }
        
        $queryFormData = $this->queryFormHelper->prepareCommonViewData($this->branch_model, $this->platform_model);
        $this->setViewData($queryFormData);
        
        cachecontrol::set(array(
            'etag'     => $params,
            'expires'  => time() + ( 60 * 60 )
        ));
        
        $items_per_page = Kohana::config('search.number_results_advanced_search');
        $meta = $this->_prepareReportsMetaArray();
        $page = Input::instance()->get('page');
        $page = (!empty($page)) ? $page : 1;
        $pager = null;
        $reports = array();
        $signature_to_bugzilla = array();

        if ($params['do_query'] !== FALSE) {
            $Bugzilla = new Bugzilla;

            $totalCount = $this->common_model->queryTopSignatures($params, 'count');
            $pager = new MozPager($items_per_page, $totalCount, $page);
            
            if ($reports = $this->common_model->queryTopSignatures($params, 'results', $items_per_page, $pager->offset)) {
                $reports = $this->_prepareReports($reports);
                $meta = $this->_prepareReportsMeta($reports);
            } 
            
            $rows = $this->bug_model->bugsForSignatures($meta['signatures']);
            $signature_to_bugzilla = $Bugzilla->signature2bugzilla($rows, Kohana::config('codebases.bugTrackingUrl'));
        }
        
        $this->setViewData(array(
            'items_per_page' => $items_per_page,
            'nav_selection' => 'query',
            'navPathPrefix' => url::site('query') . '?' . html::query_string($params) . "&page=",
            'nextLinkText' => 'next >>',
            'page' => $page,
            'pager' => $pager, 
            'params'  => $params,
            'previousLinkText' => '<< prev',
            'reports' => $reports,
            'showPluginName' => $meta['showPluginName'],
            'showPluginFilename' => $meta['showPluginFilename'],
            'sig2bugs' => $signature_to_bugzilla,
            'totalItemText' => " Results",
            'url_nav' => url::site('products/'.$this->chosen_version['product']),
        ));
    }

}
