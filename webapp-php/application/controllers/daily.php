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
    private function csvURL ($product, $versions, $operating_systems, $date_start, $date_end, $form_selection, $throttle) {
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
        
        // Prepare variables
        $products = Kohana::config('daily.products');
        $operating_systems = Kohana::config('daily.operating_systems');
        
        // Fetch $_GET variables.
        $parameters = $this->input->get();		
        $product = (isset($parameters['p']) && in_array($parameters['p'], $products)) ? $parameters['p'] : 'Firefox';
        $operating_system = (isset($parameters['os'])) ? $parameters['os'] : $operating_systems;
        $date_start = (isset($parameters['date_start'])) ? $parameters['date_start'] : date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-15, date("Y")));
        $date_end = (isset($parameters['date_end'])) ? $parameters['date_end'] : date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-1, date("Y")));
        $duration = TimeUtil::determineDayDifferential($date_start, $date_end);
        $dates = $this->model->prepareDates($date_end, $duration);
        $form_selection = (isset($parameters['form_selection']) && $parameters['form_selection'] == 'by_os') ? $parameters['form_selection'] : 'by_version';
        
        // If no version is available, include the most recent version of this product
        if (isset($parameters['v']) && !empty($parameters['v'])){
	    $versions = $this->_filterInvalidVersions($product, $parameters['v']);
        } 
        if (!isset($versions) || count($versions) == 0 || empty($versions[0])) {
            $current_products = $this->currentProducts();
            $versions = array();
            foreach (array(Release::MAJOR, Release::MILESTONE, Release::DEVELOPMENT) as $release) {
                if (isset($current_products[$product][$release])) {
                    $versions[] = $current_products[$product][$release];
                }
            }
        }
        if ( isset($parameters['hang_type'])) {
	    $hang_type = $parameters['hang_type'];
	} else {
            $hang_type = 'any';
	}
        
        // Determine throttling rates
        $throttle = null;
        if (isset($parameters['throttle']) && !empty($parameters['throttle'])) {
            $throttle = $parameters['throttle'];
        }         
        if (count($throttle) == 0 || empty($throttle[0])) {
            $throttle = array();
            $throttle_key = 0;
            $throttle_rates = Kohana::config('daily.throttle_rates');            
            $product_versions = $this->branch_model->getProductVersionsByProduct($product);
            foreach ($versions as $version) {
                if (isset($throttle_rates[$product][$version])) {
                    $throttle[$throttle_key] = $throttle_rates[$product][$version];
                }

                if (!isset($throttle[$throttle_key])) {
                    $throttle[$throttle_key] = 100;
                }
                $throttle_key++;
            }
        }
        
		// Prepare URL for CSV
		$url_csv = $this->csvURL($product, $versions, $operating_systems, $date_start, $date_end, $form_selection, $throttle);

        // Statistics on crashes for time period
	$results = $this->model->get($product, $versions, $operating_system, $date_start, $date_end, $hang_type);
        $statistics = $this->model->prepareStatistics($results, $form_selection, $product, $versions, $operating_system, $date_start, $date_end, $throttle);
        $graph_data = $this->model->prepareGraphData($statistics, $form_selection, $date_start, $date_end, $dates, $operating_systems, $versions);
        
        // Download the CSV, if applicable
        if (isset($parameters['csv'])) {
        	return $this->csv($product, $versions, $operating_systems, $dates, $results, $statistics, $form_selection, $throttle);
        }
        
        // Set the View
        $this->setViewData(array(
                'date_start' => $date_start,
                'date_end' => $date_end,
                'dates' => $dates,
                'duration' => $duration,
                'file_crash_data' => 'daily/daily_crash_data_' . $form_selection,
                'form_selection' => $form_selection,
                'graph_data' => $graph_data,
                'nav_selection' => 'crashes_user',
                'operating_system' => $operating_system,
                'operating_systems' => $operating_systems,              
                'product' => $product,                          
                'products' => $products,
                'hang_type' => $hang_type,
                'results' => $results,
                'statistics' => $statistics,
                'throttle' => $throttle,
                'url_csv' => $url_csv,
                'url_form' => url::site("daily", 'http'),                               
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
     * @return array of strings
     */
    private function _filterInvalidVersions($product, $version_inputs)
    {
        return $this->branch_model->verifyVersions($product, $version_inputs);
    }
}
