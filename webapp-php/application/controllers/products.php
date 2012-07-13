<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

require_once(Kohana::find_file('libraries', 'release', TRUE, 'php'));

/**
 * The controller for products / versions dashboards.
 */
class Products_Controller extends Controller {

    /**
     * Number of duration days selected
     */
    public $duration;

    /**
     * Number of duration displaying starts for within the dashboard.  Used in $this->_determineDuration().
     */
    public $duration_options = array(3, 7, 14, 28);

    /**
     * $_GET parameters.
     */
    public $parameters;

    /**
     * Class constructor.
     *
     * @return void
     */
    public function __construct()
    {
        parent::__construct();
        $this->parameters = $this->input->get();

        $this->daily_model = new Daily_Model;
        $this->duration = $this->_determineDuration();
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
     * Determine the value for $this->duration for a given page.
     *
     * @return  int    The $this->duration value in days
     */
    private function _determineDuration()
    {
        if (isset($this->parameters['duration'])) {
            $duration = (int)$this->parameters['duration'];
            if (in_array($duration, $this->duration_options)) {
                return $duration;
            }
        }
        return Kohana::config('products.duration');
    }

    /**
     * Determine the starting date used in a web service call.
     *
     * @return  string  Y-M-D
     */
    private function _determineDateStart()
    {
        return date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-($this->duration+1), date("Y")));
    }

    /**
     * Determine the ending date used in a web service call.
     *
     * @return  string  Y-M-D
     */
    private function _determineDateEnd()
    {
        return date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-1, date("Y")));
    }

    /**
      * Grab the throttle from an existing prod / version without needing to hit the db.
      *
      * @param   string  Product name
      * @param   string  Version name
      * @return  int     The throttle value
      */
     private function _determineThrottle($product, $version)
     {
         $throttle = 100;
         if (isset($this->featured_versions) && !empty($this->featured_versions)) {
             foreach ($this->featured_versions as $featured_version) {
                 if ($product == $featured_version->product && $version == $featured_version->version) {
                     $throttle = $featured_version->throttle;
                 }
             }
         }
         if (isset($this->unfeatured_versions) && !empty($this->featured_versions)) {
             foreach ($this->unfeatured_versions as $unfeatured_version) {
                 if ($product == $unfeatured_version->product && $version == $unfeatured_version->version) {
                     $throttle = $unfeatured_version->throttle;
                 }
             }
         }
         return $throttle;
     }

    /**
     * Determine the number of top changing top crashes that should be
     * displayed on the dashboard.
     *
     * @return  int
     */
    private function _determineTopchangersCountDashboard()
    {
        $topchangers_count = Kohana::config('products.topchangers_count_dashboard');
        return (!empty($topchangers_count)) ? $topchangers_count : 15;
    }

    /**
     * Determine the number of top changing top crashes that should be
     * displayed on the full page.
     *
     * @return  int
     */
    private function _determineTopchangersCountPage()
    {
        $topchangers_count = Kohana::config('products.topchangers_count_page');
        return (!empty($topchangers_count)) ? $topchangers_count : 50;
    }

    /**
     * Determine which signatures are the top crashers for this product
     *
     * @param   string   A product name
     * @return  array    An array of top crashers
     */
    private function _determineTopcrashersProduct($product)
    {
        $top_crashers = array();
        $i = 0;
        foreach($this->featured_versions as $featured_version) {
            $top_crashers[$i] = $this->topcrashers_model->getTopCrashersViaWebService(
                $product,
                $featured_version->version,
                $this->duration
            );
            $top_crashers[$i]->product = $product;
            $top_crashers[$i]->version = $featured_version->version;
            $i++;
        }
        return $top_crashers;
    }

    /**
     * Determine which signatures are the top changers given
     * an array of top crashers.
     *
     * @param   string  The product name
     * @param   string  The version number
     * @param   array   An array of top crashers
     * @param   bool    TRUE to include the downward trending topcrashers; FALSE if not
     * @param   int     The number of topchangers to include
     * @return  array   An array of top changers
     */
    private function _determineTopchangersProductVersion($product, $version, $top_crashers, $trend_down=true, $topchangers_count) {
        if (isset($top_crashers->crashes) && !empty($top_crashers->crashes)) {
            $changers = array();
            foreach($top_crashers->crashes as $key => $top_crasher) {
                $tc_key = $top_crasher->changeInRank.'.'.$key;
                if (!in_array($top_crasher->changeInRank, array('new', 0))) {
                    $changers[$tc_key] = array(
                        'currentRank' => $top_crasher->currentRank,
                        'changeInRank' => $top_crasher->changeInRank,
                        'signature' => $top_crasher->signature,
                        'trendClass' => $top_crasher->trendClass,
                        'url' => $this->_formatTopchangerURL($product, $version, $top_crasher)
                    );
                }
        }

            if (!empty($changers)) {
                $top_changers = array('up' => array());
                krsort($changers);
                for ($i = 1; $i <= $topchangers_count; $i++) {
                    $top_changers['up'][] = array_shift($changers);
            }

                if ($trend_down) {
                    $top_changers['down'] = array();
                    ksort($changers);
                    for ($i = 1; $i <= $topchangers_count; $i++) {
                        $top_changers['down'][] = array_shift($changers);
                    }
                }

                return $top_changers;
            }
        }
        return false;
    }

    /**
     * Prepare top changers data for top crashers that have more than one version.
     *
     * @param   string  The product name
     * @param   array   An array of top crashers
     * @param   int     The number of versions being displayed on this page
     * @param   bool    TRUE to include the downward trending topcrashers; FALSE if not
     * @param   int     The total number of topchangers to include
     * @return  array   An array of top changers
     */
    private function _determineTopchangersProduct($product, $top_crashers, $versions_count, $trend_down=true, $topchangers_count) {
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
                                'currentRank' => $top_crasher->currentRank,
                                'changeInRank' => $top_crasher->changeInRank,
                                'signature' => $top_crasher->signature,
                                'trendClass' => $top_crasher->trendClass,
                                'url' => $this->_formatTopchangerURL($product, null, $top_crasher)
                            );
                        } else {
                            $top_changers['currentRank'] += $top_crasher->currentRank;
                            $top_changers['changeInRank'] += $top_crasher->changeInRank;
                        }
                    }
                }

                foreach($top_changers as $top_changer) {
                    if (!in_array($top_changer['changeInRank'], array('new', 0))) {
                        $tc_key = $top_changer['changeInRank'].'.'.$key;
                        $changers[$tc_key] = array(
                            'currentRank' => ceil($top_changer['currentRank'] / $versions_count),
                            'changeInRank' => $top_changer['changeInRank'],
                            'signature' => $top_changer['signature'],
                            'trendClass' => $top_changer['trendClass'],
                            'url' => $top_changer['url']
                        );
                    }
                }
            }
        }

        if (isset($changers) && !empty($changers)) {
            $top_changers = array('up' => array());
            krsort($changers);
            for ($i = 1; $i <= $topchangers_count; $i++) {
                $top_changers['up'][] = array_shift($changers);
            }

            if ($trend_down) {
                $top_changers['down'] = array();
                ksort($changers);
                for ($i = 1; $i <= $topchangers_count; $i++) {
                    $top_changers['down'][] = array_shift($changers);
                }
            }

            return $top_changers;
        }
        return false;
    }

    /**
     * Format the URL for a top changer signature.
     *
     * @param   string  The product
     * @param   string  The version (optional)
     * @param   array  The top crasher object
     * @return  string The URL for the signature
     */
    private function _formatTopchangerURL($product, $version=null, $top_crasher)
    {
        $range_value = $this->duration;
        $range_unit = 'days';

        $sigParams = array(
            'range_value' => $range_value,
            'range_unit'  => $range_unit,
            'signature' => $top_crasher->signature,
            'version' => $product
        );

        if (!empty($version)) {
            $sigParams['version'] .= ":" . $version;
        }

        return url::base() . 'report/list?' . html::query_string($sigParams);
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
        $this->chooseVersion(
            array(
                'product' => trim($product),
                'version' => null,
                'release' => null,
            )
        );
        $this->prepareVersions(); // Update the featured and unfeatured versions
    }

    /**
      * Display CSV file for a product / version.
      *
      * @param   string  The product name
      * @param   string  The version number
      * @param   array   An array of top changers
      * @return  void
      */
    private function _topchangersCSV($product, $version=null, $top_changers)
    {
        $product_version = $product;
        $product_version .= (!empty($version)) ? $version : '';

        $heading = array('Current Rank', 'Change in Rank', 'Signature');
        $csvData = array($heading);
        if (!empty($top_changers)) {
            foreach ($top_changers as $tc) {
                foreach ($tc as $top_changer) {
                    array_push($csvData, array(
                        $top_changer['currentRank'],
                        $top_changer['changeInRank'],
                        strtr($top_changer['signature'], array(',' => ' ', '\n' => ' ', '"' => '&quot;'))
                    ));
                }
            }
        }

        $title = "Top_Changers_" . $product . "_" . $version . "_" . $this->duration . "_days_" . date("Y-m-d");
        $this->setViewData(array('top_crashers' => $csvData));
        $this->renderCSV($title);
    }

    /**
     * Display RSS feeds for top changing top crashers.
     *
     * @param   string  The product name
     * @param   string  The version number
     * @param   array   An array of top changers
     * @return  void
     */
    private function _topchangersRSS($product, $version=null, $top_changers)
    {
        $title = "Top Changing Top Crashers for " . $product . " for the past " . $this->duration . " days";
        if (isset($version) && !empty($version)) {
            $title .= " " . $version;
        }
        $info = array("title" => $title);

        $items = array();
        if (isset($top_changers) && !empty($top_changers)) {
            foreach($top_changers as $tc) {
                foreach ($tc as $top_changer) {
                    $title = ucfirst($top_changer['trendClass']) . ' ' . $top_changer['changeInRank'] . ' to Top Crasher #' . $top_changer['currentRank'] . ' - ' . html::specialchars($top_changer['signature']);
                    $pubdate = date("r", time());
                    $items[] = array(
                        'title' => $title,
                        'link' => html::specialchars($top_changer['url']),
                        'description' => $title,
                        'pubDate' => $pubdate
                    );
                }
            }
        }
        echo feed::create($info, $items);
        exit;
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
     * @param   string  The next method to point to.  'builds', 'topchangers' or null
     * @param   bool    True if requesting rss feed of data; false if not
     * @return  void
     */
    public function index($product=null, $version=null, $call=null, $rss=false)
    {
        if (empty($product)) {
            $this->products();
        } elseif (in_array($product, $this->current_products)) {
            $this->_productSelected($product);

            if (!empty($version)) {
                $this->_versionSelected($product, $version);
                if ($this->versionExists($version)) {
                    if ($call == 'builds') {
                        $this->productVersionBuilds($product, $version, $rss);
                    } elseif ($call == 'topchangers') {
                        $this->productVersionTopchangers($product, $version, $rss);
                    } else {
                        $this->productVersion($product, $version);
                    }
                } else {
                    Kohana::show_404();
                }
            } else {
                $this->_productSelected($product);
                if ($call == 'builds') {
                    $this->productBuilds($product, $rss);
                } elseif ($call == 'topchangers') {
                    $this->productTopchangers($product, $rss);
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
        $date_start = $this->_determineDateStart();
        $date_end = $this->_determineDateEnd();
        $dates = $this->daily_model->prepareDates($date_end, $this->duration);
        $operating_systems = Kohana::config('daily.operating_systems');
        $url_csv = '';

        $productVersions = $this->branch_model->getProductVersionsByProduct($product);
        $versions = array();
        foreach ($productVersions as $productVersion) {
            $versions[] = $productVersion->version;
        }

        $top_crashers = array();
        $daily_versions = array();
        $num_signatures = Kohana::config("products.topcrashers_count");
        $i = 0;
        if (! $this->featured_versions) {
          $this->setView('products/error');
          $this->setViewData(
             array(
               'product' => $product,
               'error' => 1
             )
          );
          return;
        }
        foreach($this->featured_versions as $featured_version) {
            $top_crashers[$i] = $this->topcrashers_model->getTopCrashersViaWebService(
                $product,
                $featured_version->version,
                $this->duration
            );
            $top_crashers[$i]->product = $product;
            $top_crashers[$i]->version = $featured_version->version;

            $daily_versions[] = $featured_version->version;
            $throttle[] = $featured_version->throttle;
            $i++;
        }
        $top_changers = $this->_determineTopchangersProduct($product, $top_crashers, count($this->featured_versions), true, $this->_determineTopchangersCountDashboard());

        $results = $this->daily_model->get($product, $daily_versions, $operating_systems, $date_start, $date_end, 'any');
        $statistics = $this->daily_model->prepareStatistics($results, 'by_version', $product, $daily_versions, $operating_systems, $date_start, $date_end, $throttle);
        $graph_data = $this->daily_model->prepareGraphData($statistics, 'by_version', $date_start, $date_end, $dates, $operating_systems, $daily_versions);

        $this->setView('products/product');
        $this->setViewData(
            array(
               'dates' => $dates,
               'duration' => $this->duration,
               'graph_data' => $graph_data,
               'nav_selection' => 'overview',
               'num_signatures' => $num_signatures,
               'operating_systems' => $operating_systems,
               'product' => $product,
               'results' => $results,
               'statistics' => $statistics,
               'top_changers' => $top_changers,
               'topchangers_full_page' => false,
               'top_crashers' => $top_crashers,
               'top_crashers_limit' => Kohana::config('products.topcrashers_count'),
               'url_base' => url::site('products/'.$product),
               'url_csv' => $url_csv,
               'url_nav' => url::site('products/'.$product),
               'url_top_crashers' => url::site('topcrasher/byversion/'.$product),
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
        $Build_Model = new Build_Model;
        $builds = $Build_Model->getBuildsByProduct($product, $this->duration);

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
            $dates = $Build_Model->prepareDates($date_end, $this->duration);

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
     * Display the top changing top crashers for a product.
     *
     * @param   string  The product name
     * @param   bool    True if requesting rss feed of data; false if not
     * @return  void
     */
    public function productTopchangers($product, $extension=false)
    {
        $top_crashers = $this->_determineTopcrashersProduct($product);
        $top_changers = $this->_determineTopchangersProduct($product, $top_crashers, count($this->featured_versions), false, $this->_determineTopchangersCountPage());

        if ($extension == 'rss') {
            $this->_topchangersRSS($product, null, $top_changers);
        } elseif ($extension == 'csv') {
            $this->_topchangersCSV($product, null, $top_changers);
        } else {
            $versions = array();
            foreach ($this->featured_versions as $featured_version) {
                $versions[] = $featured_version->version;
            }

            $this->setView('products/product_topchangers');
            $this->setViewData(
                array(
                    'duration' => $this->duration,
                    'nav_selection' => 'top_changers',
                    'product' => $product,
                    'top_changers' => $top_changers,
                    'topchangers_full_page' => true,
                    'url_base' => url::site('products/'.$product),
                    'url_csv' => 'products/'.$product.'/topchangers.csv?duration='.$this->duration,
                    'url_nav' => url::site('products/'.$product),
                    'url_rss' => 'products/'.$product.'/topchangers.rss?duration='.$this->duration,
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
        $date_start = $this->_determineDateStart();
        $date_end = $this->_determineDateEnd();
        $dates = $this->daily_model->prepareDates($date_end, $this->duration);
        $operating_systems = Kohana::config('daily.operating_systems');
        $throttle = $this->_determineThrottle($product, $version);
        $url_csv = '';

        $productVersions = $this->branch_model->getProductVersionsByProduct($product);
        $versions = array();
        foreach ($productVersions as $productVersion) {
            $versions[] = $productVersion->version;
        }

        $results = $this->daily_model->get($product, array($version), $operating_systems, $date_start, $date_end, 'any');
        $statistics = $this->daily_model->prepareStatistics($results, 'by_version', $product, array($version), $operating_systems, $date_start, $date_end, array($throttle));
        $graph_data = $this->daily_model->prepareGraphData($statistics, 'by_version', $date_start, $date_end, $dates, $operating_systems, array($version));

        $num_signatures = Kohana::config("products.topcrashers_count");

        $tc = $this->topcrashers_model->getTopCrashersViaWebService($product, $version, $this->duration);
        $top_crashers = array(0 => $tc);
        $top_crashers[0]->product = $product;
        $top_crashers[0]->version = $version;

        $top_changers = $this->_determineTopchangersProductVersion($product, $version, $tc, true, $this->_determineTopchangersCountDashboard());

        $this->setView('products/product_version');
        $this->setViewData(
            array(
               'dates' => $dates,
               'duration' => $this->duration,
               'graph_data' => $graph_data,
               'nav_selection' => 'overview',
               'num_signatures' => $num_signatures,
               'operating_systems' => $operating_systems,
               'product' => $product,
               'results' => $results,
               'statistics' => $statistics,
               'top_changers' => $top_changers,
               'topchangers_full_page' => false,
               'top_crashers' => $top_crashers,
               'top_crashers_limit' => Kohana::config('products.topcrashers_count'),
               'url_base' => url::site('products/'.$product.'/versions/'.$version),
               'url_csv' => $url_csv,
               'url_nav' => url::site('products/'.$product),
               'url_top_crashers' => url::site('topcrasher/byversion/'.$product.'/'.$version),
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
        $Build_Model = new Build_Model;
        $builds = $Build_Model->getBuildsByProductAndVersion($product, $version, $this->duration);

        if ($rss) {
            $this->_buildsRSS($product, $version, $builds);
        } else {
            $date_end = date('Y-m-d');
            $dates = $Build_Model->prepareDates($date_end, $this->duration);

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
     * Display the top changing top crashers for a version of a product.
     *
     * @param   string  The product name
     * @param   string  The version name
     * @param   string  'rss', 'csv', or false
     * @return  void
     */
    public function productVersionTopchangers($product, $version, $extension=false)
    {
        $tc = $this->topcrashers_model->getTopCrashersViaWebService($product, $version, $this->duration);
        $top_crashers = array(0 => $tc);
        $top_crashers[0]->product = $product;
        $top_crashers[0]->version = $version;
        $top_changers = $this->_determineTopchangersProductVersion($product, $version, $tc, false, $this->_determineTopchangersCountPage());

        if ($extension == 'rss') {
            $this->_topchangersRSS($product, null, $top_changers);
        } elseif ($extension == 'csv') {
            $this->_topchangersCSV($product, null, $top_changers);
        } else {
            $this->setView('products/product_topchangers');
            $this->setViewData(
                array(
                   'duration' => $this->duration,
                   'nav_selection' => 'top_crashers',
                   'product' => $product,
                   'top_changers' => $top_changers,
                   'topchangers_full_page' => true,
                   'url_base' => url::site('products/'.$product.'/versions/'.$version),
                   'url_nav' => url::site('products/'.$product),
                   'url_top_crashers' => url::site('topcrasher/byversion/'.$product.'/'.$version),
                   'version' => $version
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
}
