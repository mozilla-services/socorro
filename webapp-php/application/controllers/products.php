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
	    $this->daily_model = new Daily_Model;
        $this->topcrashers_model = new Topcrashers_Model;

	    cachecontrol::set(array(
            'expires' => time() + Kohana::config('products.cache_expires')
        ));
    }
    
    /**
     * Display RSS feeds for nightly builds.
     *
     * @param   string  The product name
     * @param   string  The version number
     * @param   array   An array of nightly builds
     * @return  void
     */
    public function _buildsRSS($product, $version=null, $builds)
    {        
        $title = "Crash Stats for Mozilla Nightly Builds for " . $product;
        if (isset($version) && !empty($version)) { 
            $title .= " " . $version;
        }
        $info = array("title" => $title);

        $items = array();
        if (isset($builds) && !empty($builds)) {
            foreach($builds as $build) {
                $title = $build->product . ' ' . $build->version . ' - ' . $build->platform . ' - Build ID# ' . $build->buildid;
                $link = url::base() . 'query/query?build_id=' . html::specialchars($build->buildid) . '&do_query=1';
                $pubdate = date("r", strtotime($build->date));
                $items[] = array(
                    'title' => $title,
                    'link' => html::specialchars($link),
                    'description' => $title,
                    'pubDate' => $pubdate
                );  
            }         
        }
        echo feed::create($info, $items);
        exit;
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
     * Verify that this product on this page is stored in $this->chosen_version;  If so, proceed.
     * If not, ensure that this product is stored in session and redirect the user so that My_Controller
     * will refresh with the proper selected versions.
     *
     * @param   string  The name of a product
     * @return  void
     */
    private function _productSelected($product)
    {
        if ($product != $this->chosen_version['product']) {
            $this->chooseVersion(
                array(
                    'product' => trim($product),
                    'version' => null,
                    'release' => null,
                )
            );
            $this->prepareVersions(); // Update the featured and unfeatured versions
        }
    }

    /**
     * Verify that the selected version is a valid version for this product.
     *
     * @param   string  The name of a version
     * @return  void
     */
    private function _versionExists($version)
    {
        $product_versions = array_merge($this->featured_versions, $this->unfeatured_versions);
        foreach ($product_versions as $product_version) {
            if ($product_version->version == $version) {
                return true;
            }
        }
        return false;
    }

    /**
     * Verify that this product on this page is stored in $this->chosen_version;  If so, proceed.
     * If not, ensure that this product is stored in session and redirect the user so that My_Controller
     * will refresh with the proper selected versions.
     *
     * @param   string  The name of a product
     * @param   string  The name of a version
     * @return  void
     */
    private function _versionSelected($product, $version)
    {
        if ($this->chosen_version['product'] != $product || $this->chosen_version['version'] != $version) {
            $this->chooseVersion(
                array(
                    'product' => trim($product),
                    'version' => trim($version),
                    'release' => null
                )
            );
            $this->prepareVersions(); // Update the featured and unfeatured versions
        }
    }

    /**
     * Display the dashboard for a product or a product/version combination.
     *
     * We're running all products and versions through this method in order to verify that they exist.
     *
     * @param   string  The name of a product
     * @param   string  The name of a version
     * @param   string  'builds' if the builds page should be displayed, null if not
     * @param   bool    True if requesting rss feed of data; false if not
     * @return  void
     */
    public function index($product=null, $version=null, $builds=null, $rss=false)
    {
        if (empty($product)) {
            $this->products();
        } elseif (in_array($product, $this->current_products)) {
            $this->_productSelected($product);
            
            if (!empty($version)) {
                $this->_versionSelected($product, $version);
                if ($this->_versionExists($version)) {
                    if ($builds == 'builds') {
                        $this->productVersionBuilds($product, $version, $rss);                            
                    } else {
                        $this->productVersion($product, $version);
                    }
                } else {
                    Kohana::show_404();
                }
            } else {
                $this->_productSelected($product);
                if ($builds == 'builds') {
                    $this->productBuilds($product, $rss);                            
                } else {
                    $this->product($product);
                }
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

        $top_changers = null;
        $top_crashers = array();
        $daily_versions = array();
        $num_signatures = Kohana::config("products.topcrashers_count");
        $i = 0;
        foreach($this->featured_versions as $featured_version) {
            $top_crashers[$i] = $this->topcrashers_model->getTopCrashersViaWebService(
                $product, 
                $featured_version->version, 
                $duration                    
            );
            $top_crashers[$i]->product = $product;
            $top_crashers[$i]->version = $featured_version->version;
            
            $daily_versions[] = $featured_version->version;
            $i++;
        }
        $top_changers = $this->_determineTopchangersProduct($top_crashers);
        
        $results = $this->daily_model->get($product, $daily_versions, $operating_systems, $date_start, $date_end, 'any');
        $statistics = $this->daily_model->prepareStatistics($results, 'by_version', $product, $daily_versions, $operating_systems, $date_start, $date_end, array());
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
     * Display the nightly builds page.
     *
     * @param   string  The product name
     * @param   bool    True if requesting rss feed of data; false if not
     * @return  void
     */
    public function productBuilds($product, $rss=false)
    {
        $duration = Kohana::config('products.duration');

        $Build_Model = new Build_Model;
        $builds = $Build_Model->getBuildsByProduct($product, $duration);

        if ($rss) {
            $this->_buildsRSS($product, null, $builds);
        } else {
            $versions = array();
            if (isset($builds) && !empty($builds)) {
                foreach($builds as $build) {
                    $version = $build->version;
                    if (!in_array($version, $versions)) {
                        $versions[] = $version;
                    }
                }
            }
            
            $date_end = date('Y-m-d', mktime(0, 0, 0, date("m"), date("d"), date("Y")));
            $dates = $Build_Model->prepareDates($date_end, $duration);
            
            $this->setView('products/product_builds');
            $this->setViewData(
                array(
                    'builds' => $builds,
                    'dates' => $dates,
                    'nav_selection' => 'nightlies',
                    'product' => $product,
                    'url_base' => url::site('products/'.$product),
                    'url_nav' => url::site('products/'.$product),
                    'url_rss' => 'products/'.$product.'/builds.rss',
                    'versions' => $versions
                )
            );
        }
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

        $results = $this->daily_model->get($product, array($version), $operating_systems, $date_start, $date_end, 'any');
        $statistics = $this->daily_model->prepareStatistics($results, 'by_version', $product, array($version), $operating_systems, $date_start, $date_end, array(100));
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
     * Display the dashboard for the nightly builds for a product and version.
     *
     * @param   string  The product name
     * @param   string  The version number
     * @param   bool    True if requesting rss feed of data; false if not     
     * @return  void
     */
    public function productVersionBuilds($product, $version, $rss)
    {
        $duration = Kohana::config('products.duration');

        $Build_Model = new Build_Model;
        $builds = $Build_Model->getBuildsByProductAndVersion($product, $version, $duration);

        if ($rss) {
            $this->_buildsRSS($product, $version, $builds);
        } else {
            $date_end = date('Y-m-d');
            $dates = $Build_Model->prepareDates($date_end, $duration);
            
            $this->setView('products/product_version_builds');
            $this->setViewData(
                array(
                    'builds' => $builds,
                    'dates' => $dates,
                    'nav_selection' => 'nightlies',
                    'product' => $product,
                    'url_base' => url::site('products/'.$product.'/versions/'.$version),
                    'url_nav' => url::site('products/'.$product),
                    'url_rss' => 'products/'.$product.'/versions/'.$version.'/builds.rss',
                    'version' => $version,
                    'versions' => array($version)         
                )
            );
        }

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
               'products'  => $this->current_products,
               'nav_selection' => null,
   	        )
   	    );
    }
    
    /* */
}
