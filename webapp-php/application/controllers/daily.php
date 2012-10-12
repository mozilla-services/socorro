<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Controller class for ADU, a.k.a. Active Daily Users / Installs.
 *
 * @see 		API Documentation for ADU - http://code.google.com/p/socorro/wiki/AduAPI
 * @package 	SocorroUI
 * @subpackage 	Controller
 * @author 		Ryan Snyder <rsnyder@mozilla.com>
 */
class Daily_Controller extends Controller {

    /**
     * The Daily Model.
     */
    protected $model;

    /**
     * Class Constructor
     */
    public function __construct()
    {
        parent::__construct();
    	$this->model = new Daily_Model;
    }

    /**
     * Common path for Formatting the URL for a CSV file.
     *
     * @param 	string 	The product name
     * @param 	array 	An array of versions
     * @param 	array 	An array of dates
     * @param 	array  	An array of operating systems
     * @param 	string 	The start date for the query
     * @param 	string 	The end date for the query
     * @param 	string 	The type of results display - "by_version" or "by_os"
     * @return 	string 	The url to download this CSV
     */
    private function _commonCsvURL($product, $versions, $operating_systems, $date_start, $date_end, $form_selection, $throttle)
    {
        $url 	= 'daily?p=' . html::specialchars($product);

        foreach ($versions as $version) {
        	$url .= "&v[]=" . html::specialchars($version);
        }

        foreach ($throttle as $t) {
        	$url .= "&throttle[]=" . html::specialchars($t);
        }

        foreach ($operating_systems as $operating_system) {
        	$url .= "&os[]=" . html::specialchars($operating_system);
        }

        $url .= "&date_start=" . html::specialchars($date_start);
        $url .= "&date_end=" . html::specialchars($date_end);
        $url .= "&form_selection=" . html::specialchars($form_selection);
        $url .= "&csv=1";

        return $url;
    }

    /**
     * Request for ADU - Active Daily Users aka Active Daily Installs
     *
     * @return void
     */
    public function index() {
        $branch_model = new Branch_Model;

        // Prepare variables
        $products = $branch_model->getProducts();
        $operating_systems = Kohana::config('daily.operating_systems');

        // Fetch $_GET variables.
        $parameters = $this->input->get();
        $product = (isset($parameters['p']) && in_array($parameters['p'], $products)) ? $parameters['p'] : $this->chosen_version['product'];
        $product_versions = $branch_model->getCurrentProductVersionsByProduct($product);
        $operating_system = (isset($parameters['os'])) ? $parameters['os'] : $operating_systems;
        $date_start = (isset($parameters['date_start'])) ? $parameters['date_start'] : date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-15, date("Y")));
        $date_end = (isset($parameters['date_end'])) ? $parameters['date_end'] : date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-1, date("Y")));
        $duration = TimeUtil::determineDayDifferential($date_start, $date_end);
        $dates = $this->model->prepareDates($date_end, $duration);
        $form_selection = (isset($parameters['form_selection']) && $parameters['form_selection'] == 'by_os') ? $parameters['form_selection'] : 'by_version';
        $throttle = (isset($parameters['throttle']) && !empty($parameters['throttle'])) ? $parameters['throttle'] : array();
        $hang_type = (isset($parameters['hang_type']) && $parameters['hang_type'] != 'any') ? $parameters['hang_type'] : '';
        $date_range_type = (isset($parameters['date_range_type']) ? $parameters['date_range_type'] : 'report');

        $form_selection = 'by_version';
        if (isset($parameters['form_selection']) &&
            in_array($parameters['form_selection'], array('by_os', 'by_version', 'by_report_type'))) {
        	$form_selection = $parameters['form_selection'];
        }

        // If no version is available, include the most recent version of this product
        if (isset($parameters['v']) && !empty($parameters['v'])){
            $version_inputs = $parameters['v'];
            $versions = false;
            if ($valid_versions = $this->branch_model->verifyVersions($product, $version_inputs)) {
                $versions = array();
                foreach ($version_inputs as $v) {
                    foreach ($valid_versions as $vv) {
                        if ($v == $vv) {
                            $versions[] = $v;
                            break;
                        }
                    }
                }
            }
        }
        if (!isset($versions) || count($versions) == 0 || empty($versions[0])) {
            $versions = array();
            $throttle = array();
            $featured_versions = $branch_model->getFeaturedVersions($product);
            foreach ($featured_versions as $featured_version) {
                $versions[] = $featured_version->version;
                $throttle[] = $featured_version->throttle;
            }
        }
        // if a version is provided but no throttle level,
        // we need to call the products_versions service to get the throttle level
        if(empty($throttle) && isset($versions)) {
            $response = $this->model->getVersionInfo($product, $versions);
            foreach($response->hits as $version) {
                $throttle[] = $version->throttle;
            }
        }

        $operating_system = implode("+", $operating_system);

        $url_csv = $this->_commonCsvURL($product, $versions, $operating_systems, $date_start, $date_end, $form_selection, $throttle);
        $url_csv .= "&hang_type=" . html::specialchars($hang_type);

        // For service calls versions needs to be separated by a + sign
        $versions_for_service = implode("+", $versions);
        $results = $this->model->getCrashesPerADU($product, $versions_for_service, $date_start, $date_end, $date_range_type,
                $operating_system, $hang_type, $form_selection);
        // Statistics on crashes for time period
        $statistics = $this->model->calculateStatistics($results->hits, $form_selection);
        $graph_data = $this->model->buidDataObjectForGraph($date_start, $date_end, $results->hits, $form_selection);

        $versions_in_result = array();
        foreach (get_object_vars($results->hits) as $version => $data) {
            $prod_ver = explode(":", $version);
            array_push($versions_in_result, $prod_ver[1]);
        }

        rsort($versions_in_result);

        // Download the CSV, if applicable
        if (isset($parameters['csv'])) {
            $title = "ADU_" . $product . "_" . implode("_", $versions) . "_" . $form_selection;

            $this->auto_render = FALSE;
            header('Content-type: text/csv; charset=utf-8');
            header("Content-disposition: attachment; filename=${title}.csv");

            $view = new View('daily/daily_csv_' . $form_selection);
            $view->dates = $dates;
            $view->form_selection = $form_selection;
            $view->operating_systems = $operating_systems;
            $view->product = $product;
            $view->results = $results;
            $view->statistics = $statistics;
            $view->throttle = $throttle;
            $view->versions_in_result = $versions_in_result;
            $view->versions = $versions;

            echo $view->render();
            exit;
        }

        $protocol = (Kohana::config('auth.force_https')) ? 'https' : 'http';

        // Set the View
        $this->setViewData(array(
            'date_start' => $date_start,
            'date_end' => $date_end,
            'dates' => $dates,
            'date_range_type' => $date_range_type,
            'duration' => $duration,
            'file_crash_data' => 'daily/daily_crash_data_' . $form_selection,
            'form_selection' => $form_selection,
            'graph_data' => $graph_data,
            'hang_type' => $hang_type,
            'nav_selection' => 'crashes_user',
            'operating_system' => explode("+", $operating_system),
            'operating_systems' => $operating_systems,
            'product' => $product,
            'product_versions' => $product_versions,
            'products' => $products,
            'versions_in_result' => $versions_in_result,
            'statistic_keys' => $this->model->statistic_keys($statistics, $dates),
            'statistics' => $statistics,
            'url_csv' => $url_csv,
            'url_form' => url::site("daily", $protocol),
            'url_nav' => url::site('products/'.$this->chosen_version['product']),
            'versions' => $versions,
        ));
    }
}
