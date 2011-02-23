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
     * Request for a CSV file displaying ADU statistics
     *
     * @param 	string 	The product name
     * @param 	array 	An array of versions
     * @param 	array  	An array of operating systems	
     * @param 	array 	An array of dates
     * @param 	array  	The array of results from the API
     * @param 	array 	The array of statistics processed in the model
     * @param 	string 	The type of results display - "by_version" or "by_os"
     * @param   array   The effective trottling rate (client throttle * server throttle) for each version
     * @return 	file	
     */
    private function csv($product, $versions, $operating_systems, $dates, $results, $statistics, $form_selection, $throttle) {
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
        $view->versions = $versions;
        
        echo $view->render();
        exit;
    }
	
    /**
     * Format the URL for a CSV file.
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
    private function csvURL($product, $versions, $operating_systems, $date_start, $date_end, $hang_type, $form_selection, $throttle) {
        $url = $this->_commonCsvURL($product, $versions, $operating_systems, $date_start, $date_end, $form_selection, $throttle);
        $url .= "&hang_type=" . html::specialchars($hang_type);
        return $url;
    }
 
     /**
      * Format the URL for a CSV file.
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
    private function csvReportTypeURL($product, $versions, $operating_systems, $date_start, $date_end, $report_types, $form_selection, $throttle) {
        $url = $this->_commonCsvURL($product, $versions, $operating_systems, $date_start, $date_end, $form_selection, $throttle);
        foreach ($report_types as $rt) {
            $url .= "&report_type[]=" . html::specialchars($rt);
        }        
        return $url;
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
     * Helper funciton produces a CSV friendly array
     * @param $product      string The product name
     * @param $report_types array  An array of crash report types
     * @param $dates        array  An array of dates
     * @param $stats        array  Stats results from aduByDayDetails webservice call
     *
     * @return array
     */
    private function _convertCSV($product, $report_types, $dates, $stats)
    {
        $heading = array("$product Version", 'Date', 'ADU', 'Throttle');
        foreach ($report_types as $rt) {
	        array_push($heading, $rt);
	        array_push($heading, "$rt ratio");
	    }
            $csvData = array($heading);
            foreach ($stats['versions'] as $version => $version_stats) {
                foreach ($dates as $date) {
	    	        if (array_key_exists($date, $version_stats)) {
	    	            $date_stat = $version_stats[$date];
                        $line = array($version, $date, $date_stat['users'], $date_stat['throttle']);
	    	            foreach ($report_types as $rt) {
	    	        
	    	            if (array_key_exists("${rt}_ratio", $date_stat)){
	    		            array_push($line, $date_stat[$rt]);
	    		            array_push($line, $date_stat["${rt}_ratio"]);
	    	            }
	    	        }
	    	        array_push($csvData, $line);
	    	    }
	        }
	    }
        return $csvData;
    }
	
    /**
     * Request for ADU - Active Daily Users aka Active Daily Installs
     *
     * @return void
     */
    public function index() {
        $Branch_Model = new Branch_Model;
        
        // Prepare variables
        $products = Kohana::config('daily.products');
        $operating_systems = Kohana::config('daily.operating_systems');

        $report_types = array('crash', 'oopp', 'hang_browser', 'hang_plugin');
        
        // Fetch $_GET variables.
        $parameters = $this->input->get();		
        $product = (isset($parameters['p']) && in_array($parameters['p'], $products)) ? $parameters['p'] : $this->chosen_version['product'];
        $product_versions = $Branch_Model->getCurrentProductVersionsByProduct($product);
        $operating_system = (isset($parameters['os'])) ? $parameters['os'] : $operating_systems;
        $chosen_report_types = (isset($parameters['report_type'])) ? $parameters['report_type'] : $report_types;
        $date_start = (isset($parameters['date_start'])) ? $parameters['date_start'] : date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-15, date("Y")));
        $date_end = (isset($parameters['date_end'])) ? $parameters['date_end'] : date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-1, date("Y")));
        $duration = TimeUtil::determineDayDifferential($date_start, $date_end);
        $dates = $this->model->prepareDates($date_end, $duration);
        $form_selection = (isset($parameters['form_selection']) && $parameters['form_selection'] == 'by_os') ? $parameters['form_selection'] : 'by_version';
        $throttle = (isset($parameters['throttle']) && !empty($parameters['throttle'])) ? $parameters['throttle'] : array();
        $hang_type = (isset($parameters['hang_type'])) ? $parameters['hang_type'] : 'any'; // RS :: Is this being used?
        
        $form_selection = 'by_version';
        if (isset($parameters['form_selection']) && 
            in_array($parameters['form_selection'], array('by_os', 'by_version', 'by_report_type'))) {
        	$form_selection = $parameters['form_selection'];
        }

        // If no version is available, include the most recent version of this product
        if (isset($parameters['v']) && !empty($parameters['v'])){
            $versions = $this->_filterInvalidVersions($product, $parameters['v']);
        } 
        if (!isset($versions) || count($versions) == 0 || empty($versions[0])) {
            $versions = array();
            $throttle = array();
            $featured_versions = $Branch_Model->getFeaturedVersions($product);
            foreach ($featured_versions as $featured_version) {
                $versions[] = $featured_version->version;
                $throttle[] = $featured_version->throttle;
            }
        }
        
        if (isset($parameters['form_selection']) && $parameters['form_selection'] == 'by_report_type') {
            $url_csv = $this->csvReportTypeURL($product, $versions, $operating_systems, $date_start, $date_end, $chosen_report_types, $form_selection, $throttle);

            // Statistics on crashes for time period
            $results = $this->model->getDetailsByReportType($product, $versions, $operating_system, 
            $chosen_report_types, $date_start, $date_end);
            $statistics = $this->model->prepareStatistics($results, $parameters['form_selection'], $product, $versions, $operating_system, $date_start, $date_end, $throttle);
            $graph_data = $this->model->prepareGraphData($statistics, $parameters['form_selection'], $date_start, $date_end, $dates, $operating_systems, $versions);
            
            // Download the CSV, if applicable
            if (isset($parameters['csv'])) {
                $view = new View('common/csv');
                $this->setViewData(array('top_crashers' => $this->_convertCSV($product, $chosen_report_types, $dates, $statistics)));
                $this->renderCSV("ADU_" . $product . "_" . implode("_", $versions) . "_" . implode("_", $chosen_report_types) . '_' . $form_selection);
            }
	    
        } else { // by_version or by_os
            $url_csv = $this->csvURL($product, $versions, $operating_systems, $date_start, $date_end, $hang_type, $form_selection, $throttle);

            // Statistics on crashes for time period
            $results = $this->model->get($product, $versions, $operating_system, $date_start, $date_end, $hang_type);
            $statistics = $this->model->prepareStatistics($results, $form_selection, $product, $versions, $operating_system, $date_start, $date_end, $throttle);
            $graph_data = $this->model->prepareGraphData($statistics, $form_selection, $date_start, $date_end, $dates, $operating_systems, $versions);

            // Download the CSV, if applicable
            if (isset($parameters['csv'])) {
                return $this->csv($product, $versions, $operating_systems, $dates, $results, $statistics, $form_selection, $throttle);
            }
        }
       
        $protocol = (Kohana::config('auth.force_https')) ? 'https' : 'http';
 
        // Set the View
        $this->setViewData(array(
            'chosen_report_types' => $chosen_report_types,
            'date_start' => $date_start,
            'date_end' => $date_end,
            'dates' => $dates,
            'duration' => $duration,
            'file_crash_data' => 'daily/daily_crash_data_' . $form_selection,
            'form_selection' => $form_selection,
            'graph_data' => $graph_data,
            'hang_type' => $hang_type,
            'nav_selection' => 'crashes_user',
            'operating_system' => $operating_system,
            'operating_systems' => $operating_systems,              
            'product' => $product,
            'product_versions' => $product_versions,
            'products' => $products,
            'report_types' => $report_types,
            'results' => $results,
            'statistic_keys' => $this->model->statistic_keys($statistics, $dates),
            'statistics' => $statistics,
            'throttle' => $throttle,
            'throttle_default' => Kohana::config('daily.throttle_default'),
            'url_csv' => $url_csv,
            'url_form' => url::site("daily", $protocol),                               
            'url_nav' => url::site('products/'.$product),
            'versions' => $versions,
        ));
    }
    

   /**
     * Removes invalid version numbers
     *
     * @param string $product        - Name of a product
     * @param array  $version_inputs - List of version numbers (string)
     * 
     * @return array An array of version strings
     */
    private function _filterInvalidVersions($product, $version_inputs)
    {
        if ($valid_versions = $this->branch_model->verifyVersions($product, $version_inputs)) {
            $versions = array();
            foreach ($version_inputs as $v) {
                foreach ($valid_versions as $vv) {
                    if ($v == $vv) {
                        $versions[] = $v;
                    }
                }
            }
            return $versions;
        }
        return false;
    }
}
