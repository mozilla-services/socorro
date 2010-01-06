<?php defined('SYSPATH') or die('No direct script access.');

require_once(Kohana::find_file('libraries', 'timeutil', TRUE, 'php'));

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
     * @return 	file	
     */
    private function csv($product, $versions, $operating_systems, $dates, $results, $statistics, $form_selection) {
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
    private function csvURL ($product, $versions, $operating_systems, $date_start, $date_end, $form_selection) {
        $url 	= 'daily?p=' . html::specialchars($product);
        
        foreach ($versions as $version) {
        	$url .= "&v[]=" . html::specialchars($version);
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
        $date_start = (isset($parameters['date_start'])) ? $parameters['date_start'] : date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-14, date("Y")));
        $date_end = (isset($parameters['date_end'])) ? $parameters['date_end'] : date('Y-m-d');
        $duration = TimeUtil::determineDayDifferential($date_start, $date_end);
        $form_selection = (isset($parameters['form_selection']) && $parameters['form_selection'] == 'by_os') ? $parameters['form_selection'] : 'by_version';
        
        // Prepare dates
        $dates = array();
        $date_diff = TimeUtil::determineDayDifferential($date_end, date('Y-m-d'));
        for($i = 0; $i <= $duration; $i++) {
        	$dates[] = date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-($i+$date_diff), date("Y")));
        }
        
        // If no version is available, include the most recent version of this product
        if (isset($parameters['v'])){
        	$versions = $parameters['v']; 
        } else {
        	$recent_version = $this->branch_model->getRecentProductVersion($product);
        	$versions = array(0 => $recent_version->version);
        }
        
		// Prepare URL for CSV
		$url_csv = $this->csvURL($product, $versions, $operating_systems, $date_start, $date_end, $form_selection);

        // Statistics on crashes for time period
        $results = $this->model->get($product, $versions, $operating_system, $date_start, $date_end);
        $statistics = null;
        if ($form_selection == 'by_version') { 
        	$statistics = (!empty($results)) ? $this->model->calculateStatisticsByVersion($results) : null;
        } elseif ($form_selection == 'by_os') {
        	$statistics = (!empty($results)) ? $this->model->calculateStatisticsByOS($results) : null;
        }
        
        // Download the CSV, if applicable
        if (isset($parameters['csv'])) {
        	return $this->csv($product, $versions, $operating_systems, $dates, $results, $statistics, $form_selection);
        }
        
        // Prepare the data for the Crash Graph section of the page
        $graph_data = null;
		if ($form_selection == 'by_version') { 
        	$graph_data = $this->model->prepareCrashGraphDataByVersion($date_start, $date_end, $dates, $versions, $statistics);
        } elseif ($form_selection == 'by_os') {
        	$graph_data = $this->model->prepareCrashGraphDataByOS($date_start, $date_end, $dates, $operating_systems, $statistics);
        }
        
        // Set the View
        $this->setViewData(
        	array(
                'date_start' => $date_start,
                'date_end' => $date_end,
				'dates' => $dates,
                'duration' => $duration,
				'file_crash_data' => 'daily/daily_crash_data_' . $form_selection,
                'form_selection' => $form_selection,
				'graph_data' => $graph_data,
                'operating_system' => $operating_system,
                'operating_systems' => $operating_systems,    		
                'product' => $product,                       	
                'products' => $products,
                'results' => $results,
				'statistics' => $statistics,
				'url_csv' => $url_csv,
                'url_form' => url::site("daily", 'http'),				
                'versions' => $versions,
			)
		);
    }

	/* */
}