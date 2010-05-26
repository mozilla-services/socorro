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


require_once(Kohana::find_file('libraries', 'timeutil', TRUE, 'php'));


/**
 * Model class for ADU, a.k.a. Active Daily Users / Installs.
 *
 * @package 	SocorroUI
 * @subpackage 	Models
 * @author 		Ryan Snyder <rsnyder@mozilla.com>
 */
class Daily_Model extends Model {

	/** 
	 * The timestamp for today's date.
	 */
 	public $today = 0;

	/** 
	 * The Web Service class.
	 */
 	protected $service = '';

	/**
     * Class Constructor
     */
    public function __construct()
    {
        parent::__construct();
    
        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }

		$this->service = new Web_Service($config);
		$this->today = strtotime(date('Y-m-d'));
    }

	/**
     * Prepare the statistics for Crashes per ADU by Operating System.
	 * 
	 * The idea of throttled users were implemented in Socorro 1.5 - https://bugzilla.mozilla.org/show_bug.cgi?id=539337
	 *
	 * Throttling is inputted into the UI.  It is an effective throttling of client throttling * server throttling. Reported
	 * Active Daily Users are updated according to throttling percentages.
	 *
	 * @access 	public
	 * @param 	object	The response object from the API call
	 * @param   array   An array of effective throttle rates for each version
	 * @return 	array 	An array of statistics
     */
	public function calculateStatisticsByOS ($results, $throttle)
	{
		if (!empty($results)) {
            if (!empty($throttle)) {
                $t = array_shift($throttle);
                $throttle_1 = ($t > 0) ? ($t / 100) : 1;
                $throttle_2 = 1 - $throttle_1;
                $throttle_ratio = $throttle_2 / $throttle_1;
            } else {
                $throttle_1 = 1;
                $throttle_2 = 0;
                $throttle_ratio = 0;
            }

			$statistics = array(
				'ratio' => 0.00,
				'crashes' => 0,
				'os' => array(),
                'throttle' => $throttle_1,
				'users' => 0,
			);

			foreach ($results->versions as $version) {
				foreach ($version->statistics as $v) {
				    $date = $v->date;
				    if (strtotime($date) < $this->today) {
					    $key = $v->os;
					    
					    if (!isset($statistics['os'][$key])) {
					    	$statistics['os'][$key] = array(
					    		'crashes' => 0,
					    		'users' => 0,
					    		'ratio' => 0.00,
					    	);						
					    } 				
                        
					    if (!isset($statistics['os'][$key][$date])) {
					    	$statistics['os'][$key][$date] = array(
					    		'crashes' => 0,
					    		'users' => 0,
					    		'ratio' => 0.00,
					    	);						
					    } 				

					    $throttled_crashes = $v->crashes;
					    if ($throttle_ratio > 0) {
				            $throttled_crashes += ($v->crashes * $throttle_ratio);
    					}
					    	
					    $statistics['os'][$key][$date]['crashes'] += $throttled_crashes;
                        $statistics['os'][$key][$date]['throttle'] = $throttle_1;
					    $statistics['os'][$key][$date]['users'] += $v->users;
					    
					    if ($statistics['os'][$key][$date]['crashes'] > 0 && $statistics['os'][$key][$date]['users'] > 0) {
					    	$statistics['os'][$key][$date]['ratio'] = $statistics['os'][$key][$date]['crashes'] / $statistics['os'][$key][$date]['users'];
					    } else {
					    	$statistics['os'][$key][$date]['ratio'] = 0.00;
					    }
                        
					    $statistics['crashes'] += $throttled_crashes;
					    $statistics['users'] += $v->users;

					    $statistics['os'][$key]['crashes'] += $throttled_crashes;
					    $statistics['os'][$key]['users'] += $v->users;
                        
					    if ($statistics['os'][$key]['crashes'] > 0 && $statistics['os'][$key]['users'] > 0) { 
					    	$statistics['os'][$key]['ratio'] = $statistics['os'][$key]['crashes'] / $statistics['os'][$key]['users'];
					    } else {
					    	$statistics['os'][$key]['ratio'] = 0.00;
					    }
					}
				}
			}

			if ($statistics['crashes'] > 0 && $statistics['users'] > 0) { 
				$statistics['ratio'] = round(($statistics['crashes'] / $statistics['users']), 2);
			} else {
				$statistics['ratio'] = 0.00;
			}
			
			return $statistics;
		}
		return false;
	}

	/**
     * Prepare the statistics for Crashes per ADU by Version.
	 * 
	 * The idea of throttled users were implemented in Socorro 1.5 - https://bugzilla.mozilla.org/show_bug.cgi?id=539337
	 *
	 * Throttling is inputted into the UI.  It is an effective throttling of client throttling * server throttling. Reported
	 * Active Daily Users are updated according to throttling percentages.
	 *
	 * @access 	public
	 * @param 	object	The response object from the API call
	 * @param   array   An array of effective throttle rates for each version
	 * @return 	array 	An array of statistics
     */
	public function calculateStatisticsByVersion ($results, $throttle)
	{
		if (!empty($results)) {
			$statistics = array(
				'ratio' => 0.00,
				'crashes' => 0,
				'versions' => array(),
				'users' => 0,
			);

			foreach ($results->versions as $version) {
				$key = $version->version;

                if (!empty($throttle)) {
                    $t = array_shift($throttle);
                    $throttle_1 = ($t > 0) ? ($t / 100) : 1;
                    $throttle_2 = 1 - $throttle_1;
                    $throttle_ratio = $throttle_2 / $throttle_1;
                } else {
                    $throttle_1 = 1;
                    $throttle_2 = 0;
                    $throttle_ratio = 0;
                }
                				
				$statistics['versions'][$key] = array(
					'ratio' => 0.00,
					'crashes' => 0,
					'throttle' => $throttle_1,
					'users' => 0,
					'version' => $key,
				);

				foreach ($version->statistics as $v) {
				    $date = $v->date;
				    if (strtotime($date) < $this->today) {
					    if (!isset($statistics['versions'][$key][$date])) {
					    	$statistics['versions'][$key][$date] = array(
					    		'crashes' => 0,
					    		'users' => 0,
					    		'ratio' => 0.00,
					    	);						
					    } 				
					    	
					    $throttled_crashes = $v->crashes;
					    if ($throttle_ratio > 0) {
					        $throttled_crashes += ($v->crashes * $throttle_ratio);
					    }
					    	
					    $statistics['versions'][$key][$date]['crashes'] += $throttled_crashes;
                        $statistics['versions'][$key][$date]['throttle'] = $throttle_1;
					    $statistics['versions'][$key][$date]['users'] += $v->users;

					    if ($statistics['versions'][$key][$date]['crashes'] > 0 && $statistics['versions'][$key][$date]['users'] > 0) {
					    	$statistics['versions'][$key][$date]['ratio'] = $statistics['versions'][$key][$date]['crashes'] / $statistics['versions'][$key][$date]['users'];
					    } else {
					    	$statistics['versions'][$key][$date]['ratio'] = 0.00;
					    }
                        
					    $statistics['crashes'] += $throttled_crashes;
					    $statistics['users'] += $v->users;					
					    $statistics['versions'][$key]['crashes'] += $throttled_crashes;
					    $statistics['versions'][$key]['users'] += $v->users;
					}
				}
				
				if ($statistics['versions'][$key]['crashes'] > 0 && $statistics['versions'][$key]['users'] > 0) { 
					$statistics['versions'][$key]['ratio'] = $statistics['versions'][$key]['crashes'] / $statistics['versions'][$key]['users'];
				} else {
					$statistics['versions'][$key]['ratio'] = 0.00;
				}
			}

			if ($statistics['crashes'] > 0 && $statistics['users'] > 0) { 
				$statistics['ratio'] = $statistics['crashes'] / $statistics['users'];
			} else {
				$statistics['ratio'] = 0.00;
			}
			
			return $statistics;
		}
		return false;
	}

	/**
     * Prepare an array of parameters for the url.
	 * 
	 * @access 	private
	 * @param 	array 	The array that needs to be parameterized.
	 * @return 	string 	The url-encoded string.
     */
	private function encodeArray (array $parameters) {
		$uri = '';
		$parameters = array_unique($parameters);
		$num_parameters = count($parameters);
		for ($i = 0; $i <= $num_parameters; $i++) {
			$parameter = array_shift($parameters);
			if (!empty($parameter)) {
				if ($i > 0) {
					$uri .= ";";
				}
				$uri .= urlencode($parameter);
			}
		}
		return $uri;
	}

	/**
     * Format the URL for the ADU web service call.
	 * 
	 * @access 	private
	 * @param 	string 	The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
	 * @param 	string 	The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
	 * @param       string  The Report Type [any|crash|hang]
	 * @param 	string	The start date for this product YYYY-MM-DD
	 * @param 	string	The end date for this product YYYY-MM-DD (usually +90 days)
	 * @return 	string 	The URL.
     */
	private function formatURL ($product, $versions, $hang_type, $operating_systems, $start_date, $end_date) {
		$host = Kohana::config('webserviceclient.socorro_hostname');
		
		$p = urlencode($product);
		$v = $this->encodeArray($versions);
		$os = $this->encodeArray($operating_systems);
		$start = urlencode($start_date);
		$end = urlencode($end_date);
		
		$url = $host . "/201005/adu/byday/p/".$p."/v/".$v."/rt/".$hang_type."/os/".$os."/start/".$start."/end/".$end;
		return $url;
	}
	
	/**
     * Fetch records for active daily users / installs. 
	 * 
	 * @access 	public
	 * @param 	string 	The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
	 * @param 	array 	An array of versions of this product
	 * @param 	array 	An array of operating systems to query
	 * @param 	string	The start date for this product YYYY-MM-DD
	 * @param 	string	The end date for this product YYYY-MM-DD (usually +90 days)
	 * @return 	object	The database query object
	 * @param       string  The Report Type [any|crash|hang] - defaults to 'any'
     */
	public function get($product, $versions, $operating_systems, $start_date, $end_date, $hang_type='any') {
	    $url = $this->formatURL($product, $versions, $hang_type, $operating_systems, $start_date, $end_date);
		$lifetime = Kohana::config('webserviceclient.topcrash_vers_rank_cache_minutes', 60) * 60; // number of seconds
		$response = $this->service->get($url, 'json', $lifetime);

		if (isset($response) && !empty($response)) {
			return $response;
		} else {
			Kohana::log('error', "No ADU data was avialable at \"$url\" via soc.web daily.get()");
		}
		return false;
	}
	
	/**
     * Prepare the data for the crash graph for ADU by Operating System.
	 * 
	 * @access 	public
	 * @param 	string	The start date for this product YYYY-MM-DD
	 * @param 	string	The end date for this product YYYY-MM-DD (usually +90 days)
	 * @param 	array 	An array of dates
	 * @param 	array 	An array of operating_systems
	 * @param 	array 	An array of statistics
	 * @return 	array	The array prepared for the crash data graph
     */
	public function prepareCrashGraphDataByOS($date_start, $date_end, $dates, $operating_systems, $statistics) {
		if (!empty($statistics)) {
			$data = array(
				'startDate' => $date_start,
				'endDate'   => $date_end,
				'count' 	=> count($operating_systems),
			);
			
			for($i = 1; $i <= $data['count']; $i++) {
				$key_ratio = 'ratio' . $i;
				$key_item = 'item' . $i; 
				$item = array_shift($operating_systems);
				$data[$key_item] = $item;
				$data[$key_ratio] = array();
				foreach ($dates as $date) {
				    if (strtotime($date) < $this->today) {
					    if (isset($statistics['os'][$item][$date])) {
					    	array_push($data[$key_ratio], array(strtotime($date)*1000, $statistics['os'][$item][$date]['ratio'] * 100));
					    } else {
					    	array_push($data[$key_ratio], array(strtotime($date)*1000, null));
					    }
					}
				}
			}
			return $data;
		} 
		return false;
	}
	
	/**
     * Prepare the data for the crash graph for ADU by Version.
	 * 
	 * @access 	public
	 * @param 	string	The start date for this product YYYY-MM-DD
	 * @param 	string	The end date for this product YYYY-MM-DD (usually +90 days)
	 * @param 	array 	An array of dates
	 * @param 	array 	An array of version numbers
	 * @param 	array 	An array of statistics
	 * @return 	array	The array prepared for the crash data graph
     */
	public function prepareCrashGraphDataByVersion($date_start, $date_end, $dates, $versions, $statistics) {
		if (!empty($statistics)) {
			$data = array(
				'startDate' => $date_start,
				'endDate'   => $date_end,
				'count' 	=> count($versions),
			);
			
			for($i = 1; $i <= $data['count']; $i++) {
				$key_ratio = 'ratio' . $i;
				$key_item = 'item' . $i; 
				$item = array_shift($versions);
				$data[$key_item] = $item;
				$data[$key_ratio] = array();
				foreach ($dates as $date) {
				    if (strtotime($date) < $this->today) {
					    if (isset($statistics['versions'][$item][$date])) {
					    	array_push($data[$key_ratio], array(strtotime($date)*1000, $statistics['versions'][$item][$date]['ratio'] * 100));
					    } else {
					    	array_push($data[$key_ratio], array(strtotime($date)*1000, null));
					    }
					}
				}
			}
			
			return $data;
		} 
		return false;
	}

    /**
     * Prepare the dates that will be used for statistic collection.
     *
     * @param   string  The end date
     * @param   int     The number of dates to query
     * @return  array   
     */
    public function prepareDates($date_end, $duration) {
        $dates = array();
        $date_diff = TimeUtil::determineDayDifferential($date_end, date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-1, date("Y"))));
        for($i = 0; $i <= $duration; $i++) {
            $date = date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-($i+$date_diff), date("Y")));
            if (strtotime($date) < $this->today) { 
        	    $dates[] = $date;
        	}
        }
        return $dates;
    }

    /**
     * Prepare the Crash Data for the Crash Graphs.
     *
     * @param   array   The array of crash data statistics
     * @param   string  The graph type, whether reporting by version or by O/S
     * @param   string  The start date
     * @param   string  The end date
     * @param   array   The array of O/S that will be reported
     * @param   array   The array of versions that will be reported  
     * @return  array   
     */
    public function prepareGraphData($statistics, $form_selection='by_version', $date_start, $date_end, $dates, $operating_systems=null, $versions=null)
    {
        $graph_data = null;
		if ($form_selection == 'by_version') { 
        	$graph_data = $this->prepareCrashGraphDataByVersion($date_start, $date_end, $dates, $versions, $statistics);
        } elseif ($form_selection == 'by_os') {
        	$graph_data = $this->prepareCrashGraphDataByOS($date_start, $date_end, $dates, $operating_systems, $statistics);
        }
        return $graph_data;
    }

    /**
     * Prepare the Crash Data for the Crash Graphs.
     *
     * @param   array   The array of crash stats data results
     * @param   string  The graph type, whether reporting by version or by O/S
     * @param   string  The product name
     * @param   array   An array of versions
     * @param   array   An array of operating systems
     * @param   string  The start date
     * @param   string  The end date
     * @param   array   An array of effective throttling rates for each version
     * @return  array   The array of crash stats data statistics
     */
    public function prepareStatistics($results, $form_selection='by_version', $product, $versions, $operating_system, $date_start, $date_end, $throttle) {
        $statistics = null;
        if ($form_selection == 'by_version') { 
        	$statistics = (!empty($results)) ? $this->calculateStatisticsByVersion($results, $throttle) : null;
        } elseif ($form_selection == 'by_os') {
        	$statistics = (!empty($results)) ? $this->calculateStatisticsByOS($results, $throttle) : null;
        }
        return $statistics;
    }

	/* */
}
