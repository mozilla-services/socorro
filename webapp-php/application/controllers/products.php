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
 
require_once(Kohana::find_file('libraries', 'release', TRUE, 'php'));

/**
 * The controller for products / versions dashboards.
 */
class Products_Controller extends Controller {

    /**
     * Number of duration displaying starts for within the dashboard.
     */
    public $duration = array(7, 14, 28);

    /**
     * Class constructor.
     *
     * @return void
     */
    public function __construct()
    {
        parent::__construct();
	    $this->branch_model = new Branch_Model;
	    $this->daily_model = new Daily_Model;
        $this->topcrashers_model = new Topcrashers_Model;

	    $products = $this->branch_model->getProducts();
	    $this->products = array();
	    foreach ($products as $product) {
	        $this->products[] = $product->product;
	    }
	    
	    cachecontrol::set(array(
            'expires' => time() + Kohana::config('products.cache_expires')
        ));
    }
    
    /**
     * Determine which signatures are the top changers
     *
     * @param   array   An array of top crashers
     * @return  array   An array of top changers
     */
    private function _determineTopchangers($top_crashers) {
        $req_props = array(
            'signature' => '',
            'changeInRank' => 0 
        );
        
        $changers = array();
	    foreach($top_crashers as $top_crasher) {
	        foreach ($top_crasher['crashers'] as $key => $crasher) {
    	        $this->topcrashers_model->ensureProperties($crasher, $req_props, 'Could not find changeInRank');
        		$crasher->trendClass = $this->topcrashers_model->addTrendClass($crasher->changeInRank);

                $tc_key = $crasher->changeInRank.'.'.$key;
                $changers[$tc_key] = array(
                    'changeInRank' => $crasher->changeInRank,
                    'signature' => $crasher->signature,
                    'trendClass' => $crasher->trendClass,
                );
	        }
	    }
	    
	    $topchangers_count = Kohana::config('products.topchangers_count');
	    $top_changers = array(
	        'up' => array(), 
	        'down' => array()
	    );
	    
	    krsort($top_changers); 
        for ($i = 1; $i <= $topchangers_count; $i++) {
            $top_changers['up'][] = array_shift($changers);
	    }

	    ksort($top_changers); 
        for ($i = 1; $i <= $topchangers_count; $i++) {
            $top_changers['down'][] = array_shift($changers);
	    }
        
        return $top_changers;
    }

    /**
     * Display the dashboard for a product or a product/version combination.
     *
     * @param   string  The name of a product
     * @param   string  The name of a version
     * @return  void
     */
    public function index($product=null, $version=null)
    {
        if (empty($product)) {
            $this->products();
        } elseif (in_array($product, $this->products)) {
            if (!empty($version)) {
                $productVersions = $this->branch_model->getProductVersionsByProduct($product);
                $version_found = false;
                foreach ($productVersions as $productVersion) {
                    if ($productVersion->version == $version) {
                        $version_found = true;
                        $this->chooseVersion(
                            array(
                                'product' => $product,
                                'version' => $version,
                                'release' => null
                            )
                        );
                        $this->productVersion($product, $version);
                    }
                }
                
                if (!$version_found) {
                    Kohana::show_404();
                }
            } else {
                $this->chooseVersion(
                    array(
                        'product' => $product,
                        'version' => null,
                        'release' => null
                    )
                );
                $this->product($product);
            }
        } else {
            Kohana::show_404();
        }
    }  
    
    /**
     * Display the dashboard for a product.
     *
     * @return  void
     */
    public function product($product)
    {
        $parameters = $this->input->get();

        $duration = (isset($parameters['duration']) && in_array($parameters['duration'], $this->duration)) ? $parameters['duration'] : Kohana::config('products.duration');
        $date_start = date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-($duration+1), date("Y")));
        $date_end = date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-1, date("Y")));
        $dates = $this->daily_model->prepareDates($date_end, $duration);
        $operating_systems = Kohana::config('daily.operating_systems');
        $url_csv = '';

        $productVersions = $this->branch_model->getProductVersionsByProduct($product);
        $versions = array();
        foreach ($productVersions as $productVersion) {
            $versions[] = $productVersion->version;
        }

        $current_products = $this->currentProducts();
        $top_crashers = array();
        $daily_versions = array();
        $num_signatures = Kohana::config("products.topcrashers_count");
        foreach (array(Release::MAJOR, Release::DEVELOPMENT, Release::MILESTONE) as $release) {
            if (isset($current_products[$product][$release]) && !empty($current_products[$product][$release])) {
                $current_version = $current_products[$product][$release];
                $end = $this->topcrashers_model->lastUpdatedByVersion($product, $current_version);
                $start = $this->topcrashers_model->timeBeforeOffset($duration, $end);

                $key = $product . "_" . $current_version;
                $top_crashers[$key] = array(
                    'product' => $product,
                    'version' => $current_version,
                    'crashers' => $this->topcrashers_model->getTopCrashersByVersion(
                        $product, $current_version, $num_signatures, $start, $end
                    )
                );
                $daily_versions[] = $current_version;
            }
        }
        
        $top_changers = $this->_determineTopchangers($top_crashers);
        
        $results = $this->daily_model->get($product, $daily_versions, $operating_systems, $date_start, $date_end);
        $statistics = $this->daily_model->prepareStatistics($results, 'by_version', $product, $daily_versions, $operating_systems, $date_start, $date_end);
        $graph_data = $this->daily_model->prepareGraphData($statistics, 'by_version', $date_start, $date_end, $dates, $operating_systems, $daily_versions);
        
        $this->setView('products/product');
        $this->setViewData(
            array(
               'dates' => $dates,
               'duration' => $duration,  
               'graph_data' => $graph_data,                       
               'nav_selection' => 'overview',
               'num_signatures' => $num_signatures,
               'operating_systems' => $operating_systems,
               'product' => $product,
               'results' => $results,
               'statistics' => $statistics,
               'top_changers' => $top_changers,
               'top_crashers' => $top_crashers,
               'url_base' => url::site('products/'.$product),
               'url_csv' => $url_csv,
               'url_nav' => url::site('products/'.$product),
               'url_top_crashers' => url::site('topcrasher/byversion/'.$product),
               'url_top_domains' => url::site('topcrasher/bydomain/'.$product),
               'url_top_topsites' => url::site('topcrasher/bytopsite/'.$product),
               'url_top_urls' => url::site('topcrasher/byurl/'.$product),
               'version' => null,
               'versions' => $versions
   	        )
   	    );
    }
    
    /**
     * Display the dashboard for a product and version.
     *
     * @param   string  The product name
     * @param   string  The version number
     * @return  void
     */
    public function productVersion($product, $version)
    {
        $parameters = $this->input->get();

        $duration = (isset($parameters['duration']) && in_array($parameters['duration'], $this->duration)) ? $parameters['duration'] : Kohana::config('products.duration');
        $date_start = date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-($duration+1), date("Y")));
        $date_end = date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-1, date("Y")));
        $dates = $this->daily_model->prepareDates($date_end, $duration);
        $operating_systems = Kohana::config('daily.operating_systems');
        $url_csv = '';

        $productVersions = $this->branch_model->getProductVersionsByProduct($product);
        $versions = array();
        foreach ($productVersions as $productVersion) {
            $versions[] = $productVersion->version;
        }

        $results = $this->daily_model->get($product, array($version), $operating_systems, $date_start, $date_end);
        $statistics = $this->daily_model->prepareStatistics($results, 'by_version', $product, array($version), $operating_systems, $date_start, $date_end);
        $graph_data = $this->daily_model->prepareGraphData($statistics, 'by_version', $date_start, $date_end, $dates, $operating_systems, array($version));
        
        $num_signatures = Kohana::config("products.topcrashers_count");
        $end = $this->topcrashers_model->lastUpdatedByVersion($product, $version);
        $start = $this->topcrashers_model->timeBeforeOffset($duration, $end);
        $top_crashers = array(
            0 => array(
                'product' => $product,
                'version' => $version,
                'crashers' => $this->topcrashers_model->getTopCrashersByVersion(
                    $product, $version, $num_signatures, $start, $end
                )
            )
        );
        
        $top_changers = $this->_determineTopchangers($top_crashers);
        
        $this->setView('products/product_version');
        $this->setViewData(
            array(
               'dates' => $dates,
               'duration' => $duration,  
               'graph_data' => $graph_data,                       
               'nav_selection' => 'overview',
               'num_signatures' => $num_signatures,
               'operating_systems' => $operating_systems,
               'product' => $product,
               'results' => $results,
               'statistics' => $statistics,
               'top_changers' => $top_changers,
               'top_crashers' => $top_crashers,
               'url_base' => url::site('products/'.$product.'/versions/'.$version),
               'url_csv' => $url_csv,
               'url_nav' => url::site('products/'.$product),
               'url_top_crashers' => url::site('topcrasher/byversion/'.$product.'/'.$version),
               'url_top_domains' => url::site('topcrasher/bydomain/'.$product.'/'.$version),
               'url_top_topsites' => url::site('topcrasher/bytopsite/'.$product.'/'.$version),
               'url_top_urls' => url::site('topcrasher/byurl/'.$product.'/'.$version),
               'version' => $version,
               'versions' => $versions
   	        )
   	    );
    }
    
    /**
     * When no products have been selected, show a list of all current products to choose from.
     *
     * @return  void
     */
    public function products()
    {
        $this->setView('products/products'); 
        $this->setViewData(
            array(
               'base_url' => url::site('products'),
               'products'  => $this->products,
               'nav_selection' => null,
   	        )
   	    );
    }
    
    /* */
}
