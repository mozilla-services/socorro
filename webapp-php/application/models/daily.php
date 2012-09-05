<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
     * Returns the correct UI string for the provided OS
     *
     * @param string    operating system name
     * @return string   correctly formatted OS string
     */
    private function getOSDisplayName($os)
    {
        $formattedOS = "";

        if(stripos($os, "win") !== false) {
            $formattedOS = Kohana::config('platforms.win_name');
        } else if(stripos($os, "mac") !== false) {
            $formattedOS = Kohana::config('platforms.mac_name');
        } else if(stripos($os, "lin") !== false) {
            $formattedOS = Kohana::config('platforms.lin_name');
        } else {
            $formattedOS = "Unsupported OS Name.";
        }
        return $formattedOS;
    }

    /**
     *
     */
    public function calculateOverallTotal($product_data, $report_type='by_version')
    {
        $product_info = array();
        $versions = array();
        $os = array();
        $total_users = 0;
        $total_crashes = 0;
        $ratio = 0.00;

        // Extract the version data
        foreach (get_object_vars($product_data) as $key => $data) {
            $current_key = explode(':', $key);
            if($report_type != 'by_os') {
                array_push($versions, $current_key[1]);
            } else {
                array_push($os, $this->getOSDisplayName($current_key[2]));
            }

            $product_info = $data;
        }

        // Loop through all items and total up the amounts
        foreach ($product_info as $key => $current_item) {
            $ratio += $current_item->crash_hadu;
            $total_crashes += $current_item->report_count;
            $total_users += $current_item->adu;
        }

        $statistics['ratio']  = $ratio;
        $statistics['crashes'] = $total_crashes;
        $statistics['users'] = $total_users;
        if($report_type != 'by_os') {
            $statistics['versions'] = $versions;
        } else {
            $statistics['os'] = $os;
        }

        if ($statistics['crashes'] > 0 && $statistics['users'] > 0) {
            $statistics['ratio'] = round(($statistics['crashes'] / $statistics['users']), 2);
        } else {
            $statistics['ratio'] = 0.00;
        }

        return $statistics;
    }

    /**
     *
     */
    public function calculateTotalByVersion($statistics, $version_data)
    {
        // Extract the version data
        foreach (get_object_vars($version_data) as $version => $data) {
            // We only want the version string not including the product name
            $prod_ver = explode(':', $version);
            $key = $prod_ver[1];
            $ratio = 0.00;
            $total_crashes = 0;
            $throttle = 0;
            $total_users = 0;

            $statistics['versions'][$key] = array();

            // Loop through the data for the current version and total up the amounts
            foreach ($data as $date => $current_version) {
                $ratio += $current_version->crash_hadu;
                $total_crashes += $current_version->report_count;
                $throttle = $current_version->throttle;
                $total_users += $current_version->adu;

                if (strtotime($date) < $this->today) {
                    if (!isset($statistics['versions'][$key][$date])) {
                        $statistics['versions'][$key][$date] = array(
                            'crashes' => $current_version->report_count,
                            'users' => $current_version->adu,
                            'ratio' => $current_version->crash_hadu,
                        );
                    }
                }
            }

            $statistics['versions'][$key]['ratio'] = $ratio;
            $statistics['versions'][$key]['crashes'] = $total_crashes;
            $statistics['versions'][$key]['throttle'] = $throttle;
            $statistics['versions'][$key]['users'] = $total_users;
            $statistics['versions'][$key]['version'] = $key;
        }

        return $statistics;
    }

    /**
     *
     */
    public function calculateTotalByOS($statistics, $os_data)
    {
        // Extract the OS data
        foreach (get_object_vars($os_data) as $os => $data) {
            $prod_ver_os = explode(':', $os);
            $key = $this->getOSDisplayName($prod_ver_os[2]);
            $ratio = 0.00;
            $total_crashes = 0;
            $throttle = 0;
            $total_users = 0;

            $statistics['os'][$key] = array();

            foreach ($data as $date => $current_os) {
                $ratio += $current_os->crash_hadu;
                $total_crashes += $current_os->report_count;
                $throttle = $current_os->throttle;
                $total_users += $current_os->adu;

                if (!isset($statistics['os'][$key][$date])) {
                    $statistics['os'][$key][$date] = array(
                        'crashes' => $current_os->report_count,
                        'users' => $current_os->adu,
                        'ratio' => $current_os->crash_hadu,
                    );

                    if ($statistics['os'][$key][$date]['crashes'] > 0 && $statistics['os'][$key][$date]['users'] > 0) {
                        $statistics['os'][$key][$date]['ratio'] = $statistics['os'][$key][$date]['crashes'] / $statistics['os'][$key][$date]['users'];
                    } else {
                        $statistics['os'][$key][$date]['ratio'] = 0.00;
                    }
                }
            }

            $statistics['os'][$key]['ratio'] = $ratio;
            $statistics['os'][$key]['crashes'] = $total_crashes;
            $statistics['os'][$key]['throttle'] = $throttle;
            $statistics['os'][$key]['users'] = $total_users;
            $statistics['os'][$key]['os'] = $key;
        }

        return $statistics;
    }

    /**
     *
     */
    public function calculateStatistics($results, $report_type)
    {
        $statistics = $this->calculateOverallTotal($results, $report_type);

        if ($report_type == 'by_version') {
            $statistics = $this->calculateTotalByVersion($statistics, $results);
        } elseif ($report_type == 'by_os') {
            $statistics = $this->calculateTotalByOS($statistics, $results);
        }

        return $statistics;
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

            $this->calculateTotalForProduct($results);

			$statistics = array(
				'ratio' => 0.00,
				'crashes' => 0,
				'versions' => array(),
				'users' => 0,
			);

			foreach ($results as $key => $version_data) {

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

    private function _sortVersions($versions)
    {
        $sorted_versions_array = array();

        foreach ($versions as $key => $value) {
            array_push($sorted_versions_array, $key);
        }

        usort($sorted_versions_array, function ($a, $b) {
            return ($a > $b) ? -1 : 1;
        });

        return $sorted_versions_array;
    }

    private function _sortVersionData($version_data)
    {
        $sorted_version_data_array = array();

        foreach ($version_data as $item) {
            array_push($sorted_version_data_array, $item);
        }

        usort($sorted_version_data_array, function ($a, $b) {
            return ($a->date < $b->date) ? -1 : 1;
        });

        return $sorted_version_data_array;
    }

    /**
     * Build data object for front page graph.
     *
     * @access public
     * @param  string  The start date for this product YYYY-MM-DD
     * @param  string  The end date for this product YYYY-MM-DD
     * @param  object  The individual items from which we extract the ratios for the graph
     * @return array   The compiled data for the front page graph
     */
    public function buidDataObjectForGraph($date_start=null, $date_end=null, $response_items=null, $report_type='by_version')
    {
        $count = count(get_object_vars($response_items));
        $counter = 1;
        $cadu = array();

        $data = array(
            'startDate' => $date_start,
            'endDate'   => $date_end,
            'count'     => $count,
        );

        foreach ($response_items as $version => $version_data) {
            if ($counter <= $count) {
                $key_ratio = 'ratio' . $counter;

                $cadu[$key_ratio] = array();
                array_push($cadu[$key_ratio], $version);

                $version_data_array = $this->_sortVersionData($version_data);
                foreach ($version_data_array as $details) {
                    if(strtotime($details->date) < $this->today) {
                        array_push($cadu[$key_ratio], array(strtotime($details->date) * 1000, $details->crash_hadu));
                    }
                }
            }
            $counter++;
        }

        $data['cadu'] = $cadu;

        usort($data['cadu'], function ($a, $b) {
            return ($a[0] > $b[0]) ? -1 : 1;
        });

        return $data;
    }

    private function _buildDataObjectForCrashReports($response_items)
    {
        $crashReports = array();
        $prod_ver = array();

        $version_array = $this->_sortVersions($response_items);

        foreach ($version_array as $version) {

            if (strrpos($version, ":")) {
                $products_versions = explode(":", $version);
            }

            $prod_ver['product'] = $products_versions[0];
            $prod_ver['version'] = $products_versions[1];

            array_push($crashReports, $prod_ver);
        }

        return $crashReports;
    }

    /**
     * Build the service URI from the paramters passed and returns the URI with
     * all values rawurlencoded.
     *
     * @param array url parameters to append and encode
     * @param string the main api entry point ex. crashes
     * @return string service URI with all values encoded
     */
    public function buildURI($params, $apiEntry)
    {
        $separator = "/";
        $host = Kohana::config('webserviceclient.socorro_hostname');
        $apiData = array(
                $host,
                $apiEntry
        );

        foreach ($params as $key => $value) {
            $apiData[] = $key;
            $apiData[] = (is_array($value) ? $this->encodeArray($value) : rawurlencode($value));
        }

        $apiData[] = '';    // Trick to have the closing '/'

        return implode($separator, $apiData);
    }

    /**
     * Fetch records for active daily users.
     *
     * @access public
     * @param  string  The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
     * @param  string  The versions for this product
     * @param  string  The start date for this product YYYY-MM-DD
     * @param  string  The end date for this product YYYY-MM-DD
     * @param  string  The date range for which to fetch record. Should be either 'build' or 'report'
     * @param  string  The string of operating systems selected for this report.
     * @param  string  The hang type selected for this report. Can be one of crash, oopp, hang browser, hang plugin
     * @param  string  The report type selectd, can be one of by_version, by_os, by_report_type
     * @return array   The compiled data for the front page graph or Crashes per ADU
     */
    public function getCrashesPerADU($product=null, $versions=null, $start_date=null, $end_date=null,
        $date_range_type=null, $operating_systems=null, $report_types=null, $form_selection='by_version')
    {
        $graph_data = array();
        $isDataForGraph = TRUE;

        $params['product'] = $product;
        $params['versions'] = $versions;
        $params['from_date'] = $start_date;
        $params['to_date']  = $end_date;
        $params['date_range_type'] = $date_range_type;

        if ($operating_systems != null) {
            $isDataForGraph = FALSE;
            $params['os'] = $operating_systems;
            // Operating systems can be specified for by version as well but,
            // we only want to separate the results by OS if the selected,
            // report type was by_os.
            if($form_selection == 'by_os') {
                $params['separated_by'] = 'os';
            }
        }

        if ($report_types != null) {
            $params['report_type'] = $report_types;
            $params['separated_by'] = 'report_type';
        }

        $url = $this->buildURI($params, "crashes/daily");
        $lifetime = Kohana::config('webserviceclient.topcrash_vers_rank_cache_minutes', 60) * 60; // number of seconds
        $response = $this->service->get($url, 'json', $lifetime);

        if (isset($response) && !empty($response)) {
            // If true, data is for the frontpage
            if ($isDataForGraph) {
                $graph_data = $this->buidDataObjectForGraph($start_date, $end_date, $response->hits);
                $graph_data['productVersions'] = $this->_buildDataObjectForCrashReports($response->hits);
                return $graph_data;
            }
            return $response;
        }
        return false;
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
}
