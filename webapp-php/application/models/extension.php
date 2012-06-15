<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Common model class managing the extensions table.
 *
 * @author 	Ryan Snyder	<ryan@foodgeeks.com>
 * @package	Socorro
 * @subpackage 	Models
 */
class Extension_Model extends Model {

    /**
     * The Web Service class.
     */
    protected $service = null;

    public function __construct()
    {
        parent::__construct();

        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }

        $this->service = new Web_Service($config);
    }

	/**
	* Cache the results from the AMO API call.
	*
	* @access 	private
	* @param 	string 	The URL for the AMO API call
	* @return 	array|bool 	An array of extensions from AMO; false if expired
	*/
	private function cacheResults($url, $results) {
		if (!empty($results)) {
			$cache = new Cache();
			$cache->set($this->getCacheKey($url), $results);
		}
	}

	/**
     * Take an array of extensions and return that same array with enhanced data about each extension.
	 *
	 * 1. Pull the GUIDs out of the extensions array.
	 * 2. Query the AMO API for meta data about those extensions.
	 * 3. Merge the data into the current extension array.
	 * 4. Flag all extensions that are out of date.
     *
 	 * @access	public
     * @param  	array 	An array of installed extensions
 	 * @param 	string 	The product that crashed ('firefox', 'thunderbird', 'seamonkey', 'sunbird')
     * @return 	array  	The array of installed extensions merged with meta data for those extensions
     */
    public function combineExtensionData($extensions, $product='firefox')
    {
		if (!empty($extensions) && is_array($extensions)) {
			$guids = array();
			foreach ($extensions as $extension) {
				$guids[] = rawurlencode($extension->extension_id);
			}
			$amo_extensions = $this->getExtensionsFromAMO($guids);

			$link_prefix = Kohana::config('application.amo_url') . 'en-US/' . strtolower(rawurlencode($product)) . '/addon/';
			$merged_extensions = array();
			$i = 0;
			foreach ($extensions as $extension) {
				$merged_extensions[$i] = array(
					'extension_id' => $extension->extension_id,
					'name' => '',
					'link' => '',
					'extension_version' => $extension->extension_version, // version installed at time of crash
					'latest_version' => '',
				);

				if (!empty($amo_extensions)) {
					foreach ($amo_extensions as $amo_id => $ae) {
						if ($extension->extension_id == $ae->guid) {
							$merged_extensions[$i]['name'] = $ae->name; // name of extension
							$merged_extensions[$i]['link'] = $link_prefix . $amo_id; // link to AMO website
							$merged_extensions[$i]['latest_version'] = $ae->latest_version; // current version according to AMO
						}
					}
				}
				$i++;
			}

			if (!empty($merged_extensions)) {
				return $merged_extensions;
			}
		}
		return false;
	}

	/**
	* Return the cache key for the AMO API call.
	*
	* @access 	private
	* @param 	string 	The url for the API call
	* @return 	string	The cache key
	*/
	private function getCacheKey($url) {
		return 'amo_api_' . md5($url);
	}

	/**
	* Fetch the cached results for an AMO API call, if available.
	*
	* @access 	private
	* @param 	string 	The URL for the AMO API call
	* @return 	array|bool 	An array of extensions from AMO; false if expired
	*/
	private function getCachedAMOExtensions($url) {
		$cache = new Cache();
        if ($results = $cache->get($this->getCacheKey($url))) {
            return $results;
        }
		return false;
	}

	/**
	* Query the AMO API for more information about the Extensions installed in the
	* browser upon crash.
	*
	* Sample URL to reference once the API call is available.
	* https://services.addons.mozilla.org/en-US/firefox/api/search/guid:
	* %7B20a82645-c095-46ed-80e3-08825760534b%7D,%7B972ce4c6-7e08-4474-a285-3208198ce6fd%7D?format=json
	*
	* @access 	private
	* @param 	array 	An array of extension GUIDs
	* @param 	string 	The product that crashed ('firefox', 'thunderbird', 'seamonkey', 'sunbird')
	* @return 	array|bool 	An array of json-decoded API results; false if empty
	*/
	private function getExtensionsFromAMO($guids, $product='firefox') {
		$url 	 = Kohana::config('application.amo_api');
		$url 	.= 'en-US/' . strtolower(rawurlencode($product)) . '/api/search/guid:';
		$url 	.= implode(",", $guids) . '?format=json';

		if ($results = $this->getCachedAMOExtensions($url)) {
			return $results;
		} else {
			$curl = curl_init($url);
			curl_setopt($curl, CURLOPT_CONNECTTIMEOUT, 30);
			curl_setopt($curl, CURLOPT_TIMEOUT, 30);
			curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
			curl_setopt($curl, CURLOPT_CUSTOMREQUEST, 'GET');
			$curl_response = curl_exec($curl);
	 		$header  = curl_getinfo($curl);
			$http_status_code = $header['http_code'];
			curl_close($curl);

			if ($http_status_code == 200) {
				$results = json_decode($curl_response);
				if (count($guids) != count($results)) {
					Kohana::log('error', "`soc.web extensions.getExtensionsFromAMO` - AMO API Call " . $url . " only returns " . count($results) . " results.  Expected " . count($guids) . " results.");
				}
				$this->cacheResults($url, $results);
				return $results;
			} else {
				Kohana::log('error', "`soc.web extensions.getExtensionsFromAMO` - AMO API Call " . $url . " returns 0 results.  Expected " . count($guids) . " results.");
			}
			return false;
		}
	}

	/**
     * Fetch all of the extensions that are installed in a browser at the time of crash.
     *
     * @param  	string 	UUID by which to look up report
 	 * @param 	string 	The date / time of the crash, e.g. '2009-10-01 08:00:40.832089'
 	 * @param 	string 	The product that crashed ('firefox', 'thunderbird', 'seamonkey', 'sunbird')
     * @return 	object 	Report data and dump data OR NULL
     */
    public function getExtensionsForReport($uuid, $date, $product='firefox')
    {
        $uri = Kohana::config('webserviceclient.socorro_hostname') . '/extensions/uuid/' . urlencode($uuid) . '/date/' . urlencode($date) . '/';
        $res = $this->service->get($uri);
        $extensions = $res->hits;

		if (!empty($extensions)) {
			return $this->combineExtensionData($extensions, $product);
		}
		return false;
	}
}
