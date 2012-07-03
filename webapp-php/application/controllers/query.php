<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

require_once(Kohana::find_file('libraries', 'bugzilla', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'crash', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'MY_SearchReportHelper', TRUE, 'php'));

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
        $this->search_model = new Search_Model;
        $this->crash = new Crash;
        $this->searchReportHelper = new SearchReportHelper;
    }

    /**
     * Format and return an array of option types for queries.
     *
     * @return  array   An array of option types.
     */
    private function _option_types()
    {
        if (Kohana::config('webserviceclient.middleware_implementation') == 'ES')
        {
            return array(
                'default'    => 'has terms',
                'exact'      => 'is exactly',
                'contains'   => 'contains',
                'startswith' => 'starts with'
            );
        }
        return array(
            'exact'      => 'is exactly',
            'contains'   => 'contains',
            'startswith' => 'starts with'
        );
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
        $params['admin'] = $this->logged_in;

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

        // Handle simple queries.  Determine if searching for OOID or Signature.
        if (isset($_GET['query_type']) && $_GET['query_type'] == 'simple') {
            if (!empty($params['query'])) {
                $crash = new Crash();
                $ooid = $crash->parseOOID($params['query']);

                if ($ooid !== FALSE) {
                    return url::redirect('report/index/' . $ooid);
                } else {
                    $params['query_search'] = 'signature';
                    $params['query_type'] = 'exact';
                    $params['range_value'] = 1;
                    $params['range_unit'] = 'weeks';
                }
            }
        }

        $branch_data = $this->branch_model->getBranchData();
        $platforms   = $this->platform_model->getAll();

        $versions_by_product = array();
        foreach($branch_data['versions'] as $version){
            if (!array_key_exists($version->product, $versions_by_product)) {
                $versions_by_product[$version->product] = array();
            }
            array_push($versions_by_product[$version->product], $version);
        }

        $versions_by_product_reversed = array();
        foreach ($versions_by_product as $product => $versions) {
            $versions_by_product_reversed[$product] = array_reverse($versions);
        }

        $this->setViewData(array(
            'all_products'  => $branch_data['products'],
            'all_versions'  => $branch_data['versions'],
            'versions_by_product'  => $versions_by_product,
            'all_platforms' => $platforms
        ));

        cachecontrol::set(array(
            'etag'     => $params,
            'expires'  => time() + ( 60 * 60 )
        ));

        $page = (int)Input::instance()->get('page');
        $page = (!empty($page) && $page > 0) ? $page : 1;
        $pager = null;
        $items_per_page = Kohana::config('search.number_results_advanced_search');
        $items_per_page = (!empty($items_per_page)) ? $items_per_page : 100;
        $meta = $this->crash->prepareCrashReportsMetaArray();
        $reports = array();
        $signature_to_bugzilla = array();

        if ($params['do_query'] !== FALSE) {
            $reportsData = $this->search_model->search($params, $items_per_page, ( $page - 1 ) * $items_per_page);

            if ($reportsData) {
                $totalCount = $reportsData->total;
                $pager = new MozPager($items_per_page, $totalCount, $page);

                if ($totalCount > 0) {
                    $reports = $this->crash->prepareCrashReports($reportsData->hits);
                    $meta = $this->crash->prepareCrashReportsMeta($reports);
                    $signature_to_bugzilla = $this->bug_model->bugsForSignatures(
                                                 $meta['signatures'],
                                                 Kohana::config('codebases.bugTrackingUrl')
                                             );
                }
            }
        }

        $this->setViewData(array(
            'items_per_page' => $items_per_page,
            'nav_selection' => 'query',
            'navPathPrefix' => url::site('query') . '?' . html::query_string($params) . '&page=',
            'nextLinkText' => 'next >>',
            'option_types' => $this->_option_types(),
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
            'middlewareImplementation' => Kohana::config('webserviceclient.middleware_implementation'),
        ));
    }
}
