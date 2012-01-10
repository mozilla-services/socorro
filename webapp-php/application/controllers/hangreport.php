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

        $p = urlencode($product);
        $v = urlencode($version);
        $pg = urlencode($page);
        $resp = $this->hangreport_model->getHangReportViaWebService($p, $v, $duration, $pg);

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
