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
 *   Austin King <aking@mozilla.com> (Original Author)
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

require_once(Kohana::find_file('libraries', 'Correlation', TRUE, 'php'));

/**
 * Non-visual controller for adding Correlation reports to a page.
 *
 * @author     	Austin King <aking@mozilla.com>
 */
class Correlation_Controller extends Controller 
{
    /**
     * Handel an AJAX request based on various parameters. Respond with an HTML fragment
     * suitable for loading in the page.
     *
     * @param - Must be one of cpu, addon, addonversion, module, or moduleversion
     * @param - A Product
     * @param - A Version
     * @param - A Platform, must be one of Mac OS X, Windows, Windows NT, Linux
     * @param - A top crashing signature
     */
    public function ajax($type, $product, $version, $platform, $signature)
    {
	$this->auto_render = FALSE;
	set_time_limit  (60 * 5); // Up to 5 minutes to download and parse files from people
	$types = array('cpu'           => 'core-counts',
		       'addon'         => 'interesting-addons',
		       'addonversion'  => 'interesting-addons-with-versions',
		       'module'        => 'interesting-modules',
		       'moduleversion' => 'interesting-modules-with-versions');
	if (array_key_exists($type, $types)) {
	    $day = date('Ymd'); //'20100112';

	    $correlation = new Correlation;
	    
	    $report_name = $types[$type];

	    $cache = new Cache(Kohana::config('correlation.caching'));

	    $cache_key = $this->_getCacheKey($day, $product, $version, $report_name, $signature);
            $data = $cache->get($cache_key);
            if ($data) {
		Kohana::log('debug', "CACHE HIT " . $cache_key);
		$this->_ajax($type, $product, $version, $platform, $signature, $data);
                return;
	    } else if($cache->get($this->_getGeneralCacheKey($day, $product, $version, $report_name)) === TRUE) {
		Kohana::log('debug', "CACHE HIT for NO DATA Signature" . $cache_key);
		$this->_noSignatureData($signature);
		return;
            } else {
		Kohana::log('debug', "CACHE MISS " . $cache_key);

		$report = Kohana::config('correlation.path') . "${day}/${day}_${product}_${version}-${report_name}";
		$max = 1024 * 1024 * intval(Kohana::config('correlation.max_file_size'));

		// Depending on file size, the report will be text or gzipped text. Try both
		$data = $correlation->getTxt($report . '.txt', $max);
		if ($data === FALSE) {
		    $data = $correlation->getGz($report . '.txt.gz', $max);
		} 

		if ($data !== FALSE) {
		    if (array_key_exists($signature, $data)) {
			$this->_ajax($type, $product, $version, $platform, $signature, $data[$signature]);
		    } else {
			$this->_noSignatureData($signature);
		    }
		    //cache the data
		    foreach($data as $cur_sig => $sig_data) {
			$cache_key = $this->_getCacheKey($day, $product, $version, $report_name, $cur_sig);
			$cache->set($cache_key, $sig_data);
		    }
		    //Record general access
		    $cache->set($this->_getGeneralCacheKey($day, $product, $version, $report_name), TRUE);
		    return;
		}
		echo "ERROR: No reports generated on $day for $product ${version}. Looked at ${report}.txt and ${report}.txt.gz";
	    }
	} else {
	    echo "ERROR: Unknown report type $type";
	}
    }

    /**
     * Creates a cache key for a signature
     *
     * @param - The day we are interested in Example: 20100218 - Feb 18th, 2010
     * @param - A Product
     * @param - A Version
     * @param - the name of a reports dbaron generates. Based on his filenames
     *          Example: core-counts Example: interesting-addons
     * @param - A top crashing signature
     * @return - The formatted cache key
     */
    private function _getCacheKey($day, $product, $version, $report_name, $signature)
    {
	return "correlate_${day}_${product}_${version}_${report_name}_${signature}";
    }

    /**
     * Creates a general cache key for recording that we've already loaded and parsed
     * the correlation report. Useful for knowing if we won't find a signature even
     * if we try again.
     *
     * @param - The day we are interested in Example: 20100218 - Feb 18th, 2010
     * @param - A Product
     * @param - A Version
     * @param - the name of a reports dbaron generates. Based on his filenames
     *          Example: core-counts Example: interesting-addons
     * @return - The formatted cache key
     */
    private function _getGeneralCacheKey($day, $product, $version, $report_name)
    {
	return "correlate_${day}_${product}_${version}_${report_name}";
    }

    /**
     * Generates the HTML Response when we have data
     *
     * @param - Must be one of cpu, addon, addonversion, module, or moduleversion
     * @param - A Product
     * @param - A Version
     * @param - A Platform, must be one of Mac OS X, Windows, Windows NT, Linux
     * @param - A top crashing signature
     * @param - An array of Platforms which are a key into an strings which contains the report
     *          Example: { 'Mac OS X' => ['99% (6026/6058) vs.   6% (6245/102490) overlapp32.dll',
     *                                    '66% (4010/6058) vs.  20% (20236/102490) MSCTFIME.IME'] }
     */
    private function _ajax($type, $product, $version, $platform, $signature, $data)
    {
	if ($data !== FALSE) {
	    if (array_key_exists($platform, $data)) {
		echo "<pre>" . join("\n", $data[$platform]) . "</pre>";
	    } else {
		echo "No Data for $platform when correlating $product $version $signature ";
	    }
	} else {
	    echo "Unable to load anything for $product $version at ${report}.txt or ${report}.txt.gz";
	}
    }

    /**
     * Outputs HTML for when we have no data. THis happens when we can find the 
     * general report, but this sig probably is not a top crasher and isn't in the first 2MB of data
     * @param - A signature
     */
    private function _noSignatureData($signature)
    {
	echo "Loaded Correlation Data, but non available for this signature <code>$signature</code>";
    }
}
?>