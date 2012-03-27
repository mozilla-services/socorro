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
     * Determine which stats are present in the given results
     *
     * @param $results array The results of the aduByDayDetails call
     *
     * @return array An array of report_types
     */
    private function _statKeysForResults($results)
    {
        $keys = array();
        foreach ($results->versions as $version) {
            if (property_exists($version, 'statistics')) {
                foreach ($version->statistics as $day_stats) {
                    if (property_exists($day_stats, 'crash')) {
                        array_push($keys, 'crash');
                    }
                    if (property_exists($day_stats, 'oopp')) {
                        array_push($keys, 'oopp');
                    }
                    if (property_exists($day_stats, 'hang_browser')) {
                        array_push($keys, 'hang_browser');
                    }
                    if (property_exists($day_stats, 'hang_plugin')) {
                        array_push($keys, 'hang_plugin');
                    }
                    return $keys;
                }
            }
        }
        return $keys;
    }

    /**
     * Prepare the statistics for Crashes per ADU by Version.
     *
     * Throttling is inputted into the UI.  It is an effective throttling of client throttling * server throttling. Reported
     * Active Daily Users are updated according to throttling percentages.
     *
     * Atleast one of the following will have data [crash, oop, hang_browser, hang_plugin].
     * We'll only show columns and crash events per 100 users for those datum present.
     *
     * @access      public
     *
     * @param       object  The response object from the API call
     * @param       array   An array of effective throttle rates for each version
     *
     * @return      array   An array of statistics
     */
    public function calculateStatisticsByReportType($results, $throttle)
    {
        $stat_keys = $this->_statKeysForResults($results);
        if (!empty($results)) {
            $statistics = array('versions' => array());
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
                    'throttle' => $throttle_1,
                    'users' => 0,
                    'version' => $key,
                    );

                foreach ($stat_keys as $stat_key) {
                    $statistics['versions'][$key][$stat_key] = 0;
                    $statistics['versions'][$key]["${stat_key}_ratio"] = 0.0;
                }

                foreach ($version->statistics as $v) {
                    $date = $v->date;
                    if (strtotime($date) < $this->today) {
                        if (!isset($statistics['versions'][$key][$date])) {
                            $statistics['versions'][$key][$date] = array('users' => 0);
                        }
                        foreach ($stat_keys as $stat_key) {
                            $statistics['versions'][$key][$date][$stat_key] = 0;
                            $statistics['versions'][$key][$date]["${stat_key}_ratio"] = 0.0;
                        }
                        // += because we're summing up Win, Mac, Lin...
                        if (property_exists($v, 'crash')) { $throttled_crashes = $v->crash; }
                        if (property_exists($v, 'oopp')) { $throttled_oopp = $v->oopp; }
                        if (property_exists($v, 'hang_browser')) { $throttled_hang_browser = $v->hang_browser; }
                        if (property_exists($v, 'hang_plugin')) { $throttled_hang_plugin = $v->hang_plugin; }
                        if ($throttle_ratio > 0) {
                            if (property_exists($v, 'crash')) { $throttled_crashes += $v->crash * $throttle_ratio; }
                            if (property_exists($v, 'oopp')) { $throttled_oopp += $v->oopp * $throttle_ratio; }
                            if (property_exists($v, 'hang_browser')) { $throttled_hang_browser += $v->hang_browser * $throttle_ratio; }
                            if (property_exists($v, 'hang_plugin')) { $throttled_hang_plugin += $v->hang_browser * $throttle_ratio; }
                        }

                        if (property_exists($v, 'crash')) {
                            $statistics['versions'][$key][$date]['crash'] += $throttled_crashes;
                        }
                        if (property_exists($v, 'oopp')) {
                            $statistics['versions'][$key][$date]['oopp'] += $throttled_oopp;
                        }
                        if (property_exists($v, 'hang_browser')) {
                            $statistics['versions'][$key][$date]['hang_browser'] += $throttled_hang_browser;
                        }
                        if (property_exists($v, 'hang_plugin')) {
                            $statistics['versions'][$key][$date]['hang_plugin'] += $throttled_hang_plugin;
                        }
                        $statistics['versions'][$key][$date]['throttle'] = $throttle_1;
                        $statistics['versions'][$key][$date]['users'] += $v->users;

                        if (property_exists($v, 'crash')) {
                            if ($statistics['versions'][$key][$date]['crash'] > 0 && $statistics['versions'][$key][$date]['users'] > 0) {
                                $statistics['versions'][$key][$date]['crash_ratio'] = $statistics['versions'][$key][$date]['crash'] / $statistics['versions'][$key][$date]['users'];
                            }
                        }
                        if (property_exists($v, 'oopp')) {
                            if ($statistics['versions'][$key][$date]['oopp'] > 0 && $statistics['versions'][$key][$date]['users'] > 0) {
                                $statistics['versions'][$key][$date]['oopp_ratio'] = $statistics['versions'][$key][$date]['oopp'] / $statistics['versions'][$key][$date]['users'];
                            }
                        }
                        if (property_exists($v, 'hang_browser')) {
                            if ($statistics['versions'][$key][$date]['hang_browser'] > 0 && $statistics['versions'][$key][$date]['users'] > 0) {
                                $statistics['versions'][$key][$date]['hang_browser_ratio'] = $statistics['versions'][$key][$date]['hang_browser'] / $statistics['versions'][$key][$date]['users'];
                            }
                        }
                        if (property_exists($v, 'hang_plugin')) {
                            if ($statistics['versions'][$key][$date]['hang_plugin'] > 0 && $statistics['versions'][$key][$date]['users'] > 0) {
                                $statistics['versions'][$key][$date]['hang_plugin_ratio'] = $statistics['versions'][$key][$date]['hang_plugin'] / $statistics['versions'][$key][$date]['users'];
                            }
                        }

                        if (property_exists($v, 'crash')) { $statistics['versions'][$key]['crash'] += $throttled_crashes; }
                        if (property_exists($v, 'oopp')) { $statistics['versions'][$key]['oopp'] += $throttled_oopp; }
                        if (property_exists($v, 'hang_browser')) { $statistics['versions'][$key]['hang_browser'] += $throttled_hang_browser; }
                        if (property_exists($v, 'hang_plugin')) { $statistics['versions'][$key]['hang_plugin'] += $throttled_hang_plugin; }
                        $statistics['versions'][$key]['users'] += $v->users;
                    }
                }// foreach statistics

                if (array_key_exists('crash', $statistics['versions'][$key])) {
                    if ($statistics['versions'][$key]['crash'] > 0 && $statistics['versions'][$key]['users'] > 0) {
                        $statistics['versions'][$key]['crash_ratio'] = $statistics['versions'][$key]['crash'] / $statistics['versions'][$key]['users'];
                    } else {
                        $statistics['versions'][$key]['crash_ratio'] = 0.00;
                    }
                }
                if (array_key_exists('oopp', $statistics['versions'][$key])) {
                    if ($statistics['versions'][$key]['oopp'] > 0 && $statistics['versions'][$key]['users'] > 0) {
                        $statistics['versions'][$key]['oopp_ratio'] = $statistics['versions'][$key]['oopp'] / $statistics['versions'][$key]['users'];
                    } else {
                        $statistics['versions'][$key]['oopp_ratio'] = 0.00;
                    }
                }
                if (array_key_exists('hang_browser', $statistics['versions'][$key])) {
                    if ($statistics['versions'][$key]['hang_browser'] > 0 && $statistics['versions'][$key]['users'] > 0) {
                        $statistics['versions'][$key]['hang_browser_ratio'] = $statistics['versions'][$key]['hang_browser'] / $statistics['versions'][$key]['users'];
                    } else {
                        $statistics['versions'][$key]['hang_browser_ratio'] = 0.00;
                    }
                }
                if (array_key_exists('hang_plugin', $statistics['versions'][$key])) {
                    if ($statistics['versions'][$key]['hang_plugin'] > 0 && $statistics['versions'][$key]['users'] > 0) {
                        $statistics['versions'][$key]['hang_plugin_ratio'] = $statistics['versions'][$key]['hang_plugin'] / $statistics['versions'][$key]['users'];
                    } else {
                        $statistics['versions'][$key]['hang_plugin_ratio'] = 0.00;
                    }
                }
            } // foreach versions
            return $statistics;
        }// if empty $results
        return false;
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
				$uri .= rawurlencode($parameter);
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
    private function formatURL ($api, $product, $versions, $hang_type, $operating_systems, $start_date, $end_date) {
        $host = Kohana::config('webserviceclient.socorro_hostname');

        $p = rawurlencode($product);
        $v = $this->encodeArray($versions);
        $os = $this->encodeArray($operating_systems);
        $start = rawurlencode($start_date);
        $end = rawurlencode($end_date);

        $url = $host . $api . $p . "/v/" . $v . "/rt/" . $hang_type . "/os/" . $os . "/start/" . $start . "/end/" . $end;
        return $url;
	}

    /**
     * Format the URL for the ADU web service call.
     *
     * @access      private
     * @param       string  The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
     * @param       string  The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
     * @param       string  The Report Type [any|crash|hang]
     * @param       string  The start date for this product YYYY-MM-DD
     * @param       string  The end date for this product YYYY-MM-DD (usually +90 days)
     * @return      string  The URL.
     */
    private function formatADUOverviewURL ($product, $versions, $hang_type, $operating_systems, $start_date, $end_date) {
        return $this->formatURL("/adu/byday/p/", $product, $versions, $hang_type, $operating_systems, $start_date, $end_date);
    }

    /**
     * Format the URL for the aduByDayDetails web service call.
     *
     * @access      private
     * @param       string  The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
     * @param       string  The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
     * @param       array   The Report Types
     * @param       string  The start date for this product YYYY-MM-DD
     * @param       string  The end date for this product YYYY-MM-DD (usually +90 days)
     * @return      string  The URL.
     */
    private function formatADUDetailsByReportTypeURL ($product, $versions, $report_types, $operating_systems, $start_date, $end_date) {
        $rt = $this->encodeArray($report_types);
        return $this->formatURL("/adu/byday/details/p/", $product, $versions, $rt, $operating_systems, $start_date, $end_date);
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
	    $url = $this->formatADUOverviewURL($product, $versions, $hang_type, $operating_systems, $start_date, $end_date);
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
     * Get version information that includes throttle level from products_versions service
     * 
     * @access public
     * @param string The product
     * @param string The version number
     * @return object The JSON result
     */
    public function getVersionInfo($product, $versions) {
        $host = Kohana::config('webserviceclient.socorro_hostname');
        $p = rawurlencode($product);
        $v = $this->encodeArray($versions);
        $url = $host . "/products/versions/" . $p . ":" . $v;
        
        $lifetime = Kohana::config('webserviceclient.topcrash_vers_rank_cache_minutes', 60) * 60;
        $response = $this->service->get($url, 'json', $lifetime);
        return $response;
    }

    /**
     * Fetch records for active daily users / installs by crash report type
     *
     * @access      public
     * @param       string  The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
     * @param       array   An array of versions of this product
     * @param       array   An array of operating systems to query
     * @param       array   The Report Type [crash|oopp|hang_browser|hang_plugin]
     * @param       string  The start date for this product YYYY-MM-DD
     * @param       string  The end date for this product YYYY-MM-DD (usually +90 days)
     * @return      object  The database query object
     */
    public function getDetailsByReportType($product, $versions, $operating_systems, $report_types, $start_date, $end_date) {
        $url = $this->formatADUDetailsByReportTypeURL($product, $versions, $report_types, $operating_systems, $start_date, $end_date);
        $lifetime = Kohana::config('webserviceclient.topcrash_vers_rank_cache_minutes', 60) * 60; // number of seconds
        $response = $this->service->get($url, 'json', $lifetime);

        if (isset($response) && !empty($response)) {
            return $response;
        } else {
            Kohana::log('error', "No ADU data was avialable at \"$url\" via soc.web daily.getDetailsByReportType()");
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
				$item = substr(array_shift($operating_systems), 0, 3);
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
     * Prepare the data for the crash graph for ADU by Operating System.
     *
     * What we want to create is
        [
            { 'label': '3.6.4 Crash Ratio',
              'data': [[123456777, 2.2], [1234545645, 2.3]...]},
            ...
        ]
     *
     * @access      public
     * @param       string  The start date for this product YYYY-MM-DD
     * @param       string  The end date for this product YYYY-MM-DD (usually +90 days)
     * @param       array   An array of dates
     * @param       array   An array of operating_systems
     * @param       array   An array of statistics
     * @return      array   The array prepared for the crash data graph
     */
     public function prepareCrashGraphDataByReportType($date_start, $date_end, $dates, $versions, $statistics) {
     if (!empty($statistics)) {
         $data = array();
         $keys = $this->statistic_keys($statistics, $dates);
         foreach($versions as $version) {
     	 $label = "$version Crash %";
     	 $ratio_data = array();
     	 $oopp_ratio_data = array();
     	 $hang_browser_ratio_data = array();
     	 $hang_plugin_ratio_data = array();
     	 foreach ($dates as $date) {
     	     if (strtotime($date) < $this->today) {
     	 	     if (in_array('crash', $keys)) {
     	 	         if (isset($statistics['versions'][$version][$date])) {
     	 	             array_push($ratio_data, array(strtotime($date)*1000, $statistics['versions'][$version][$date]['crash_ratio'] * 100));
     	 	         } else {
     	 	     	array_push($ratio_data, array(strtotime($date)*1000, null));
     	 	         }
     	 	     }
     	 	     if (in_array('oopp', $keys)) {
     	 	         if (isset($statistics['versions'][$version][$date])) {
     	 	             array_push($oopp_ratio_data, array(strtotime($date)*1000, $statistics['versions'][$version][$date]['oopp_ratio'] * 100));
     	 	         } else {
     	 	     	array_push($oopp_ratio_data, array(strtotime($date)*1000, null));
     	 	         }
     	 	     }
     	 	     if (in_array('hang_browser', $keys)) {
     	 	         if (isset($statistics['versions'][$version][$date])) {
     	 	             array_push($hang_browser_ratio_data, array(strtotime($date)*1000, $statistics['versions'][$version][$date]['hang_browser_ratio'] * 100));
     	 	         } else {
     	 	     	array_push($hang_browser_ratio_data, array(strtotime($date)*1000, null));
     	 	         }
     	 	     }
     	 	     if (in_array('hang_plugin', $keys)) {
     	 	         if (isset($statistics['versions'][$version][$date])) {
     	 	             array_push($hang_plugin_ratio_data, array(strtotime($date)*1000, $statistics['versions'][$version][$date]['hang_plugin_ratio'] * 100));
     	 	         } else {
     	 	     	array_push($hang_plugin_ratio_data, array(strtotime($date)*1000, null));
     	 	         }
     	 	     }
     	     }
     	 }
      	 if (in_array('crash', $keys)) {
     	     array_push($data, array('label' => "$version Crash %",
     	 			    'data'  => $ratio_data));
     	 }
     	 if (in_array('oopp', $keys)) {
     	     array_push($data, array('label' => "$version OOPP %",
     	 			    'data'  => $oopp_ratio_data));
     	 }
     	 if (in_array('hang_browser', $keys)) {
     	     array_push($data, array('label' => "$version Hang B %",
     	 			    'data'  => $hang_browser_ratio_data));
     	 }
     	 if (in_array('hang_plugin', $keys)) {
     	     array_push($data, array('label' => "$version Hang P%",
     	 			    'data'  => $hang_plugin_ratio_data));
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
        $date_diff = TimeUtil::determineDayDifferential($date_end, date('Y-m-d', mktime(0, 0, 0, date("m"), date("d"), date("Y"))));
        $timestamp = time();
        for($i = 0; $i <= $duration; $i++) {
            $date = date('Y-m-d', mktime(0, 0, 0, date("m"), date("d")-($i+$date_diff), date("Y")));
            if (strtotime($date) <= $timestamp) {
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
        } elseif ($form_selection == 'by_report_type') {
            $graph_data = $this->prepareCrashGraphDataByReportType($date_start, $date_end, $dates, $versions, $statistics);
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
        } elseif ($form_selection == 'by_report_type') {
            $statistics = (!empty($results)) ? $this->calculateStatisticsByReportType($results, $throttle) : null;
        }
        return $statistics;
    }

    /**
     * Given a set of statistics and dates determine which report_types are present.
     *
     * @param $statistics array
     * @param $dates      array
     *
     * @return array of report types
     */
    public function statistic_keys($statistics, $dates)
    {
        $keys = array();
             if (is_null($statistics)) {
            return $keys;
        }
        foreach ($dates as $date) {
            if (isset($statistics['versions']) && !empty($statistics['versions'])) {
                foreach ($statistics['versions'] as $version) {
        	    if (isset($version[$date]) &&
        	        ( isset($version[$date]['crash_ratio']) ||
        	          isset($version[$date]['oopp_ratio']) ||
        	          isset($version[$date]['hang_browser_ratio']) ||
        	          isset($version[$date]['hang_plugin_ratio']))) {
        	            $stats = $version[$date];

        	            if (array_key_exists('crash_ratio', $stats)) {
        	    	        array_push($keys, 'crash');
        	            }
        	            if (array_key_exists('oopp_ratio', $stats)) {
        	    	        array_push($keys, 'oopp');
        	            }
        	            if (array_key_exists('hang_browser_ratio', $stats)) {
        	    	        array_push($keys, 'hang_browser');
        	            }
        	            if (array_key_exists('hang_plugin_ratio', $stats)) {
        	    	        array_push($keys, 'hang_plugin');
        	            }
        	            return $keys;
    	            }
        	    }
            }
        }
        return $keys;
    }

	/* */
}
