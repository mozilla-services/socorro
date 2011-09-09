<?php
/**
 * Manage data in the topcrashers table.
 */
class Topcrashers_Model extends Model {

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
