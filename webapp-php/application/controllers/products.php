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
    private function _determineTopchangersProductVersion($top_crashers) {
        if (isset($top_crashers->crashes) && !empty($top_crashers->crashes)) {
            $changers = array();
	        foreach($top_crashers->crashes as $key => $top_crasher) {
                $tc_key = $top_crasher->changeInRank.'.'.$key;
                if (!in_array($top_crasher->changeInRank, array('new', 0))) {
                    $changers[$tc_key] = array(
                        'changeInRank' => $top_crasher->changeInRank,
                        'signature' => $top_crasher->signature,
                        'trendClass' => $top_crasher->trendClass,
                    );
                }
	        }
            
	        $topchangers_count = Kohana::config('products.topchangers_count');
	        $top_changers = array(
	            'up' => array(), 
	            'down' => array()
	        );
            
	        krsort($changers); 
            for ($i = 1; $i <= $topchangers_count; $i++) {
                $top_changers['up'][] = array_shift($changers);
	        }
            
	        ksort($changers); 
            for ($i = 1; $i <= $topchangers_count; $i++) {
                $top_changers['down'][] = array_shift($changers);
	        }
            
            return $top_changers;
        }
        return false;
    }
    
    /**
     * Prepare top changers data for top crashers that have more than one version.
     *
     * @param   array   An array of top crashers
     * @return  array   An array of top changers
     */
    private function _determineTopchangersProduct($top_crashers) {
        $crashes = array();
        $changers = array();
        
        foreach ($top_crashers as $top_crasher) {
            if (isset($top_crasher->crashes) && !empty($top_crasher->crashes)) {
                $top_changers = array();
    	        foreach($top_crasher->crashes as $key => $top_crasher) {
                    $tc_key = $top_crasher->changeInRank.'.'.$key;
                    if (!in_array($top_crasher->changeInRank, array('new', 0))) {
                        $signature = $top_crasher->signature;
                        if (!isset($top_changers['signature'])) {
                            $top_changers[$signature] = array(
                                'changeInRank' => $top_crasher->changeInRank,
                                'signature' => $top_crasher->signature,
                                'trendClass' => $top_crasher->trendClass,
                            );
                        } else {
                            $top_changers['changeInRank'] += $top_crasher->changeInRank;
                        }
                    }
    	        }
    	        
    	        foreach($top_changers as $top_changer) {
                    if (!in_array($top_changer['changeInRank'], array('new', 0))) {
    	                $tc_key = $top_changer['changeInRank'].'.'.$key;
                        $changers[$tc_key] = array(
                            'changeInRank' => $top_changer['changeInRank'],
                            'signature' => $top_changer['signature'],
                            'trendClass' => $top_changer['trendClass'],
                        );
                    }
    	        }
            }
        }

        if (isset($changers) && !empty($changers)) {
            $topchangers_count = Kohana::config('products.topchangers_count');
            $top_changers = array(
                'up' => array(), 
                'down' => array()
            );
            
            krsort($changers); 
            for ($i = 1; $i <= $topchangers_count; $i++) {
                $top_changers['up'][] = array_shift($changers);
            }
            
            ksort($changers); 
            for ($i = 1; $i <= $topchangers_count; $i++) {
                $top_changers['down'][] = array_shift($changers);
            }

            return $top_changers;
        }
        return false;
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
        $top_changers = null;
        $top_crashers = array();
        $daily_versions = array();
        $num_signatures = Kohana::config("products.topcrashers_count");
        $i = 0;
        foreach (array(Release::MAJOR, Release::MILESTONE, Release::DEVELOPMENT) as $release) {
            if (isset($current_products[$product][$release]) && !empty($current_products[$product][$release])) {
                $top_crashers[$i] = $this->topcrashers_model->getTopCrashersViaWebService(
                    $product, 
                    $current_products[$product][$release], 
                    $duration                    
                );
                $top_crashers[$i]->product = $product;
                $top_crashers[$i]->version = $current_products[$product][$release];
                $i++;
            }
        }
        
        $top_changers = $this->_determineTopchangersProduct($top_crashers);
        
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
               'top_crashers_limit' => Kohana::config('products.topcrashers_count'),
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

        $tc = $this->topcrashers_model->getTopCrashersViaWebService($product, $version, $duration);
        $top_crashers = array(0 => $tc);
        $top_crashers[0]->product = $product;
        $top_crashers[0]->version = $version;
        
        $top_changers = $this->_determineTopchangersProductVersion($tc);
        
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
               'top_crashers_limit' => Kohana::config('products.topcrashers_count'),
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
