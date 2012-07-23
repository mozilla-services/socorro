<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Manage data in the topcrashers table.
 */
class Topcrashers_Model extends Model {

    public $service = "";
    private $host = "";

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
      * Initialize the web service
      */
     public function setupWebservice() {
        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $this->service = new Web_Service($config);
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
                $apiEntry,
                "signatures"
        );

        foreach ($params as $key => $value) {
            $apiData[] = $key;
            $apiData[] = rawurlencode($value);
        }

        $apiData[] = '';    // Trick to have the closing '/'

        return implode($separator, $apiData);
    }

    /**
     * Returns top crashers from middleware service
     * 
     * @param object Contains the service url to call as well as lifetime
     * @return object the response object from the middleware
     */
    public function getTopCrashers($params)
    {
        $this->setupWebservice();
        return $this->service->get($params->{'service_uri'}, 'json', $params->{'lifetime'});
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
    	$end_date = rawurlencode(date('Y-m-d\TH:i:s+0000', TimeUtil::roundOffByMinutes($cache_in_minutes)));
    	$dur = rawurlencode($duration * 24);
    	$limit = rawurlencode(Kohana::config('topcrashbysig.byversion_limit', 300));
    	$lifetime = Kohana::config('products.cache_expires');
    	$p = rawurlencode($product);
    	$v = rawurlencode($version);

        $resp = $service->get("${host}/crashes/signatures/product/${p}/version/${v}/crash_type/browser/to_date/${end_date}/duration/${dur}/limit/${limit}",'json', $lifetime);
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
}
