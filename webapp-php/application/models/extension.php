<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Common model class managing the extensions table.
 *
 * @author 	Ryan Snyder	<ryan@foodgeeks.com>
 * @package	Socorro
 * @subpackage 	Models
 */
class Extension_Model extends Model {

	/**
     * Take an array of extensions and return that same array with enhanced data about each extension.
	 *
	 * 1. Pull the GUIDs out of the extensions array.
	 * 2. Query the AMO API for meta data about those extensions.
	 * 3. Merge the data into the current extension array.
	 * 4. Flag all extensions that are out of date.
     *
 	 * @access	public
     * @param  	array 	UUID by which to look up report
     * @return 	object 	Report data and dump data OR NULL
     */
    public function combineExtensionData(array $extensions)
    {
		$guids = array();
		foreach ($extensions as $extension) {
			$guids[] = $extension['id'];
		}
		
		if ($amo_extensions = $this->getExtensionsFromAMO($guids)) {
			$new_extensions = array();
			$i = 0;
			foreach ($extensions as $extension) {
				$new_extensions[$i];
				foreach ($amo_extensions as $guid => $ae) {
					if ($extension['id'] == $guid) {
						$new_extensions['current_version'] = $ae['version'];
						$new_extensions['name'] = $ae['name'];
						$new_extensions['link'] = 'https://addons.mozilla.org/en-US/firefox/addon/' . $guid;
					}
				}
				$i++;
			}
			return $new_extensions;
		} else {
			return $extensions;
		}
	}

	/**
	* Query the AMO API for more information about the Extensions installed in the browser upon crash.
	*
	* @access 	private
	* @param 	array 	An array of extension GUIDs
	* @return 	array 	An array of json-decoded API results
	*/
	private function getExtensionsFromAMO(array $guids) {
		
		// Sample URL to reference once the API call is available.
		// https://preview.addons.mozilla.org/en-US/firefox/api/search/guid:canuckstoolbar@canucks.nhl.com,%7B78518e5b-4eb1-0d61-ff3e-fd645642a4e2%7D/?format=json
		
		$url 	 = 'http://addons.mozilla.dev/en-US/firefox/api/1.2/search/guid:';
		$url 	.= implode(",", $guids);
		$url	.= '/?format=json';
		
		$curl = curl_init('http://addons.mozilla.com/' . $url);
		curl_setopt($curl, CURLOPT_CONNECTTIMEOUT, 30);
		curl_setopt($curl, CURLOPT_TIMEOUT, 30);
		curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
		curl_setopt($curl, CURLOPT_CUSTOMREQUEST, 'GET');
		$curl_response = curl_exec($curl);
	 	$header  = curl_getinfo($curl);
		$http_status_code = $header['http_code'];
		curl_close($curl);
		if ($http_status_code == 200) {
			return json_decode($curl_response);
		}
	}

	/**
     * Fetch all of the extensions that are installed in a browser at the time of crash.
     *
     * @param  string UUID by which to look up report
     * @return object Report data and dump data OR NULL
     */
    public function getExtensionsForReport($uuid, $date)
    {
		$sql = "/* soc.web extensions.getExtensions */
            SELECT extensions.*
			FROM extensions
			INNER JOIN reports ON extensions.report_id = reports.id
            WHERE reports.uuid = ? 
			AND reports.date_processed = ?
			AND extensions.date_processed = ?
        ";
		$extensions = $this->fetchRows($sql, true, array($uuid, $date, $date));

		if (!empty($extensions)) { 

			// Commented out until AMO API Call is available 
			// https://bugzilla.mozilla.org/show_bug.cgi?id=410277
			// return $this->combineExtensionData($extensions);
			
			return $extensions;
		}
		return false;
	}

    /* */
}
