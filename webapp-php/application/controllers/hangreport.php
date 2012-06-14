<?php defined('SYSPATH') or die('No direct script access.');

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

require_once(Kohana::find_file('libraries', 'timeutil', TRUE, 'php'));

/**
 * Reports based on hang pairs
 */
class HangReport_Controller extends Controller {

    /**
     * Constructor
     */
    public function __construct()
    {
        parent::__construct();
        $this->hangreport_model = new HangReport_Model();
    }

    /**
     * Verify that the chosen version is valid given the current product.  If
     * not, throw a 404 error.
     *
     * @return void
     */
    private function _versionExists($version) {
        if (!$this->versionExists($version)) {
            Kohana::show_404();
        }
    }

    /**
     * Generates the index page.
     */
    public function index() {
        $products = $this->featured_versions;
        $product = null;

        if(empty($products)) {
            Kohana::show_404();
        }

        foreach($products as $individual) {
            if($individual->release == 'major') {
                $product = $individual;
            }
        }

        if(empty($product)) {
            $product = array_shift($products);
        }

        return url::redirect('/hangreport/byversion/' . $product->product);
    }

    /**
     * Display the hang report by product & version.
     *
     * @param   string  The name of the product
     * @param   version The version  number for this product
     * @param   int     The number of days for which to display results
     * @param   string  The crash type to query by
     * @return  void
     */
    public function byversion($product=null, $version=null)
    {
        if(is_null($product)) {
          Kohana::show_404();
        }
        $this->navigationChooseVersion($product, $version);
        if (empty($version)) {
            $this->_handleEmptyVersion($product, 'byversion');
        } else {
            $this->_versionExists($version);
        }

        $duration = (int)Input::instance()->get('duration');
        if (empty($duration)) {
            $duration = Kohana::config('products.duration');
        }

        $page = (int)Input::instance()->get('page');
        $page = (!empty($page) && $page > 0) ? $page : 1;

        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $service = new Web_Service($config);

        $host = Kohana::config('webserviceclient.socorro_hostname');

        $cache_in_minutes = Kohana::config('webserviceclient.hang_report_cache_minutes', 60);
        $limit = Kohana::config('hang_report.byversion_limit', 300);
        // lifetime in seconds
        $lifetime = $cache_in_minutes * 60;

        $resp = $this->hangreport_model->getHangReportViaWebService($product, $version, $duration, $page);

        if ($resp) {
            $pager = new MozPager(Kohana::config('hang_report.byversion_limit'), $resp->totalCount, $resp->currentPage);

            $this->setViewData(array(
                'resp'           => $resp,
                'duration'       => $duration,
                'product'        => $product,
                'version'        => $version,
                'nav_selection'  => 'hang_report',
                'end_date'       => $resp->endDate,
                'url_base'       => url::site('hangreport/byversion/'.$product.'/'.$version),
                'url_nav'        => url::site('products/'.$product),
                'pager'          => $pager,
                'totalItemText' => " Results",
                'navPathPrefix' => url::site('hangreport/byversion/'.$product.'/'.$version) . '?duration=' . $duration . '&page=',
            ));
        } else {
            header("Data access error", TRUE, 500);
            $this->setViewData(
                array(
                   'nav_selection' => 'top_crashes',
                   'product'       => $product,
                   'url_nav'       => url::site('products/'.$product),
                   'version'       => $version,
                   'resp'          => $resp
                )
            );
        }
    }

    /**
     * Handle empty version values in the methods below, and redirect accordingly.
     *
     * @param   string  The product name
     * @param   string  The method name
     * @return  void
     */
    private function _handleEmptyVersion($product, $method) {
        $product_version = $this->branch_model->getRecentProductVersion($product);
        if (empty($product_version)) {
                // If no current major versions are found, grab any available version
            $product_versions = $this->branch_model->getCurrentProductVersionsByProduct($product);
            if (isset($product_versions[0])) {
                $product_version = array_shift($product_versions);
            }
        }

        $version = $product_version->version;
        $this->chooseVersion(
            array(
                'product' => $product,
                'version' => $version,
                'release' => null
            )
        );

        url::redirect('hangreport/'.$method.'/'.$product.'/'.$version);
    }
}
