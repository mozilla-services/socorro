<?php
/**
 * Manage data in the topcrashers table.
 */
class Topcrashers_Model extends Model {

    /**
     * Finds the time when the table was last updated for the given criteria
     * @param string A product
     * @param string A version Example 3.6a1pre
     * @return unix time or FALSE for no entries
     */
    public function lastUpdatedByVersion($product, $version) 
    {
	$sql = "/* soc.web topcrash.lastupdatebyver */ 
            SELECT max(window_end) AS last_updated
            FROM top_crashes_by_signature tcs 
            JOIN productdims p ON tcs.productdims_id = p.id
            WHERE p.product = ? AND 
                  p.version = ?";
	return $this->_lastUpdated($sql, array($product, $version));
    }

    /**
     * Common logic for fetching last updated time from the database
     * @param string sql
     * @param array params
     * @return time or FALSE if there are now entries
     */
    private function _lastUpdated($sql, $params)
    {
	$rows = $this->fetchRows($sql, TRUE, $params);
        if ($rows) {
	    // make a 2 week window
	    return strtotime($rows[0]->last_updated );
	}
	return FALSE;
    }
    
    /**
     * Return the trendClass value that will be used with this top crasher.
     *
     * @param   int     The changeInRank value
     * @return  string  The class name 
     */
    public function addTrendClass($change) {
		$trendClass = "new";
		if (is_numeric($change)) {
		    if ($change > 0) {
			    $trendClass = "up";
		    } else {
			    $trendClass = "down";
		    }
		    if (abs($change) < 5) {
			    $trendClass = "static";
		    }
		}
		return $trendClass;
	}
    
    /**
     * Utility method for checking for expected properties
     * in the output of a web service call. If any are missing
     * then an alert will be logged and a default value will be set.
     * @param object - The object that is the result of a web service call
     * @param array - An assocative array where the key is a property and the value is a default
     * @param string - A useful log msg for tracking down which 
     *                 part of the results object was missing parameters
     * @void - logs on missing properties, $crash is altered when missing properties
     */
     public function ensureProperties(&$crash, $req_props, $log_msg)
     {
 	    $missing_prop = FALSE;
 	    $missing_prop_names = array();
 	    foreach ($req_props as $prop => $default_value) {
 	        if (! property_exists($crash, $prop)) {
 		        $missing_prop = TRUE;
 		        $crash->{$prop} = $default_value;
 		        array_push($missing_prop_names, $prop);
 	        }
 	    }
 	    if ($missing_prop) {
 	        Kohana::log('alert', "Required properites are missing from $log_msg - " . implode(', ', $missing_prop_names));
 	    }
     }
    
    /**
     * Common way to process total crashes db results
     * @param string SQL to run
     * @param array Parameters bound by SQL
     * @return int Total number of crashes
     */
    private function _getTotalCrashes($sql, $params)
    {
	$tot_rows = $this->fetchRows($sql, TRUE, $params);
	if ($tot_rows) {
	    return $total_crashes = $tot_rows[0]->total;
	}
	return 0;
    }

    /**
     * Utility method for subtracting days
     * @param int Number of Days
     * @param int Date in unix time format
     * @param int New Date in unix time format
     * @see time for generating $end
     */
    public function timeBeforeOffset($days, $end)
    {
	return $end - (60 * 60 * 24 * $days);
    }
    /**
     * Utility method for formatting Postgres friendly dates
     * @param int Date in unix time format
     * @return string The formatted date
     */
    private function t($time)
    {
	return date("Y-m-d H:i:s", $time);
    }

    /**************************************************************************************************************
    topCrashersBySignature object - Dynamic Class generated from DB results in 
                                    getTopCrashersByVersion and getTopCrashersByBranch
    layout - object properties and example values:
    {
	"product":"Thunderbird",
	"version":"3.0b3",
	"signature":"nsCharTraits<char>::compareLowerCaseToASCIINullTerminated(char const*, unsigned int, char const*)",
	"percent":"0.0751807228915663",
	"total":"156",
	"win":"156","mac":"0","linux":"0"}
	
    }
    **************************************************************************************************************/

    /**
     * Find top crashes from the aggregate topcrashers table.
     * @param string product name 
     * @param string version Example: 3.7a1pre
     * @param int LIMIT for size of search results
     * @param int the earliest time to start looking for crashes
     * @param int the latest time to look at for crashes
     * @param in the total number of crashes for this period
     * @return array of topCrashersBySignature object (see comment above)
     */
    public function getTopCrashersByVersion($product=NULL, $version=NULL, $limit=100, $start=NULL, $end=NULL, $total_crashes=1) {
        $sql = "/* soc.web topcrash.byversion */ 
            SELECT p.product AS product,
                   p.version AS version,
                   tcs.signature,
                   cast(sum(tcs.count) as float) / ? as percent,
                   sum(tcs.count) as total,
                   sum(case when o.os_name LIKE 'Windows%' then tcs.count else 0 end) as win,
                   sum(case when o.os_name = 'Mac OS X' then tcs.count else 0 end) as mac,
                   sum(case when o.os_name = 'Linux' then tcs.count else 0 end) as linux 
            FROM top_crashes_by_signature tcs
            JOIN productdims p ON tcs.productdims_id = p.id
            JOIN osdims o ON tcs.osdims_id = o.id 
            WHERE p.product = ? AND 
                  p.version = ? AND 
                  window_end >= ? AND 
                  window_end < ?
            GROUP BY p.product, p.version, tcs.signature
            HAVING sum(tcs.count) > 0
            ORDER BY total desc
            LIMIT ?";
        return $this->fetchRows($sql, TRUE,
				array($total_crashes, $product, $version, $this->t($start), $this->t($end), $limit));
    }

    /**
     * Fetch the top crashers data via a web service call.
     *
     * @param   string      The product name
     * @param   string      The version number
     * @param   int         The number of days
     * @return  array       Returns 
     */
    public function getTopCrashersViaWebService($product, $version, $duration)
    {
        $config = array();
    	$credentials = Kohana::config('webserviceclient.basic_auth');
    	if ($credentials) {
    	    $config['basic_auth'] = $credentials;
    	}
    	$service = new Web_Service($config);
    	$host = Kohana::config('webserviceclient.socorro_hostname');
    	$cache_in_minutes = Kohana::config('webserviceclient.topcrash_vers_rank_cache_minutes', 60);
    	$end_date = urlencode(date('Y-m-d\TH:i:s\T+0000', TimeUtil::roundOffByMinutes($cache_in_minutes)));
    	$dur = $duration * 24;
    	$limit = Kohana::config('topcrashbysig.byversion_limit', 300);
    	$lifetime = Kohana::config('products.cache_expires');
    	$p = urlencode($product);
    	$v = urlencode($version);
        
        $resp = $service->get("${host}/201010/topcrash/sig/trend/rank/p/${p}/v/${v}/type/browser/end/${end_date}/duration/${dur}/listsize/${limit}",'json', $lifetime);
    	if($resp) {
    	    $this->ensureProperties(
    	        $resp, 
    	        array(
                    'start_date' => '',
                    'end_date' => '',
                    'totalPercentage' => 0,
                    'crashes' => array(),
                    'totalNumberOfCrashes' => 0
                ), 
                'top crash sig overall'
            );
    	
            $signatures = array();
            $req_props = array( 
                'signature' => '', 
                'count' => 0, 
            	'win_count' => 0, 
            	'mac_count' => 0, 
            	'linux_count' => 0,
                'versions' => '', 
                'versions_count' => 0,
            	'currentRank' => 0, 
            	'previousRank' => 0, 
            	'changeInRank' => 0, 
            	'percentOfTotal' => 0, 
            	'previousPercentOfTotal' => 0, 
            	'changeInPercentOfTotal' => 0
            );

            foreach($resp->crashes as $crasher) {
        	    $this->ensureProperties($crasher, $req_props, 'Could not find changeInRank');
        		$crasher->trendClass = $this->addTrendClass($crasher->changeInRank);
        		$crasher->product = $product;
        		$crasher->version = $version;
    	    }
    	    return $resp;
        }
        return false;
    }

    /**
     * Fetch all of the versions related to a crash signature for a specific product.
     *
     * @param string An array of top crashers results
     * @return string An updated array of top crashers results
     */
    function fetchTopcrasherVersions($product, $results)
    {
        if (!empty($results)) {
			$signatures = array();
            foreach($results as $result) {
				if (!empty($result->signature)) {
					array_push($signatures, $this->db->escape($result->signature));
				}
            }

            if (!empty($signatures)) { 
			    $sql = "
			    	SELECT DISTINCT 
			    	  sd.signature,
			    	  array_to_string(array_agg(pd.version ORDER BY pd.sort_key DESC),', ') as versions,
			    	  min(sd.first_report) as first_report 
                    FROM signature_productdims sd 
                    INNER JOIN productdims pd ON sd.productdims_id = pd.id 
                    WHERE sd.signature IN (" . implode(", ", $signatures) . ") 
                    AND pd.product = ? 
                    GROUP BY sd.signature
                ";
	            if ($rows = $this->fetchRows($sql, TRUE, array($product))) {
		            foreach ($results as $result) {
		                $result->first_report = null;
		                $result->versions = null;
		                $result->versions_array = array();
		                $result->versions_count = 0;
		                
			    		$versions = array();
		            	foreach($rows as $row) {
                            if ($row->signature == $result->signature) {
        			            if (!empty($row->first_report)) {
        			                $result->first_report = date("Y-m-d", strtotime($row->first_report));
                                    $result->first_report_exact = $row->first_report;
        			            }			            
        			            if (!empty($row->versions)) {
        			                $result->versions = $row->versions;
        			    			$result->versions_array = explode(",", $row->versions);
                                    $result->versions_count = count($result->versions_array);
        			    		}
			    			}
			            }
			            unset($versions);
		            }
		        }
            }
		}
		return $results;
    }

    /* */
}
