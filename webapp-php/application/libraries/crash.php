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

/**
 * Responsible for handling web service calls to retrieve crash reports from
 * the Crash Reports API.
 */
class Crash
{

    /**
     * Constant used internally to track 
     * "empty" signatures
     */
    public static $empty_sig_code = 'EMPTY_STRING';

    /**
     * Copy used for empty signatures
     */
    public static $empty_sig = '(empty signature)';

    /**
     * API value the backend web service expects for
     * "empty" signatures.
     */
    public static $empty_sig_api_value = '##empty##';

    /**
     * Constant used internally to track 
     * "null" signatures
     */
    public static $null_sig_code = 'NULL';

    /**
     * Copy used for NULL signatures
     */
    public static $null_sig = '(null signature)';

    /**
     * API value the backend web service expects for
     * "null" signatures.
     */
    public static $null_sig_api_value = '##null##';

    /**
     * The hostname that will service as a prefix for all web service calls.
     */
    public $hostname = '';

    /**
     * Instantiate the web service to prepare it for a request.
     *
     * @return void
     */
    private function _instantiateWebService()
    {
        if (empty($this->service)) { 
            $config = array();
            if ($credentials = Kohana::config('webserviceclient.basic_auth')) {
                $config['basic_auth'] = $credentials;
            }
            $this->hostname = Kohana::config('webserviceclient.socorro_hostname');
		    $this->service = new Web_Service($config);
		}
    }

    /**
    * Create the Sumo signature for this report.
    *
    * @param    string  The $signature
    * @return   string  The new signature
    */
    private function _prepareSumoSignature($signature) {
        $memory_addr = strpos($signature, '@');
        if ($memory_addr === FALSE) {
            return $signature;
        } else {
            return substr($signature, 0, $memory_addr);
        }
    }

    /**
     * Prepare an array of formatted URLs that will be used by the end user 
     * to query data, using the Socorro UI to forward a request to the Socorro
     * middleware layer.
     *
     * @param string    The $ooid for a crash report
     * @return array    An array of formatted urls.
     */
    public function formatDataURLs($ooid)
    {
        $urls = array(
            'meta' => array(
                'auth_required' => true,
                'url' => url::site('report/'.$ooid.'/meta', 'https'),
            ),
            'processed' => array(
                'auth_required' => false,
                'url' => url::site('report/'.$ooid.'/processed', 'http'),   
            ),
            'raw_crash' => array(
                'auth_required' => false,
                'url' => url::site('report/'.$ooid.'/raw_crash', 'https'),   
            ),
        );
        return $urls;
    }

    /**
     * Fetch the meta data for a crash from Hadoop.
     *
     * @param string The $ooid for a crash
     * @return object The meta data for a crash
     */
    public function getCrashMeta($ooid)
    {
        $this->_instantiateWebService();
        $url = $this->hostname . Kohana::config('application.crash_api_uri_meta') . $ooid;
		$response = $this->service->get($url, 'json', 0);
        if (!empty($response)) {
            $response->status_code = $this->service->status_code;
            return $response;
        } else {
            return false;
        }
    }

    /**
     * Fetch a processed crash from Hadoop.
     *
     * @param string The $ooid for a crash
     * @return object A crash report object
     */
    public function getCrashProcessed($ooid)
    {
        $this->_instantiateWebService();
        $url =  $this->hostname . Kohana::config('application.crash_api_uri_processed') . $ooid;
		$response = $this->service->get($url, 'json', 0);
        if (!empty($response)) {
            $response->status_code = $this->service->status_code;
            return $response;
        } else {
            return false;
        }
    }
    
    /**
     * Fetch a processed crash from Hadoop and submit a priority job at the same time.
     *
     * @param string The $ooid for a crash
     * @return object A crash report object
     */
    public function getCrashProcessedAndSubmitPriorityJob($ooid)
    {
        $this->_instantiateWebService();
        $url =  $this->hostname . Kohana::config('application.crash_api_uri_priority_processed') . $ooid;
		$response = $this->service->get($url, 'json', 0);
        if (!empty($response)) {
            $response->status_code = $this->service->status_code;
            return $response;
        } else {
            return false;
        }
    }

    /**
     * Fetch a raw dump for a crash from Hadoop.
     *
     * @param string The $ooid for a crash
     * @return object A crash report object
     */
    public function getCrashRawCrash($ooid)
    {
        $this->_instantiateWebService();
        $url = $this->hostname . Kohana::config('application.crash_api_uri_raw_crash') . $ooid;
		$response = $this->service->get($url, null, 0);
        if (!empty($response)) {
            return $response;
        } else {
            return false;
        }
    }
    
    /**
     * Parses an OOID from a string. Does not check for the existence of a crash report
     * associated with this OOID.
     * 
     * @param string input
     * @param string ooid OR FALSE
     */
    public function parseOOID($input)
    {
        if ($input) {
            $matches = array();
            $prefix = Kohana::config('application.dumpIDPrefix');
            if ( preg_match('/^('.$prefix.')?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/', $input, $matches) ) {
                $ooid = $matches[2];
                return $ooid;
            }
        }
        return false;
    }
    
    /**
     * Determine the timestamp for this report by the given UUID.
     *
     * @access  public 
     * @param   string  The $ooid for this report
     * @return  int    	The timestamp for this report.
     */
    public function parseOOIDTimestamp ($ooid)
    {
        $ooid_chunks = str_split($ooid, 6);
        if (isset($ooid_chunks[5]) && is_numeric($ooid_chunks[5])) {
            $ooid_date = str_split($ooid_chunks[5], 2);
            if (isset($ooid_date[0]) && isset($ooid_date[1]) && isset($ooid_date[2])) {
                return mktime(0, 0, 0, $ooid_date[1], $ooid_date[2], $ooid_date[0]);
            }
        }
        return false;
    }
    
    /**
     * Prepare a crash report for display.
     *
     * @param   object A crash report object
     * @param   bool If TRUE, parse the crash dump; if FALSE do not.
     * @return  object A crash report object
     */
    public function prepareCrashReport($report, $parse_dump=true)
    {
        if ((isset($report->signature) && is_null($report->signature)) || 
            (isset($report->dump) && strlen($report->dump) <= 1)) {
            $report->{'display_signature'} = Crash::$null_sig;
            $report->{'display_null_sig_help'} = TRUE;
            $report->{'missing_sig_param'} = Crash::$null_sig_code;
        } else if (empty($report->signature)) {
            $report->{'display_signature'} = Crash::$empty_sig;
            $report->{'display_null_sig_help'} = TRUE;
            $report->{'missing_sig_param'} = Crash::$empty_sig_code;
        } else {
            $report->{'display_signature'} = $report->signature;
            $report->{'display_null_sig_help'} = FALSE;
        }           

        $hang_details = array();
        $hang_details['is_hang'] = (isset($report->numhang) && $report->numhang > 0) ? true : false;
        $hang_details['is_plugin'] =  (isset($report->numplugin) && $report->numplugin > 0) ? true : false;;
        $report->{'hang_details'} = $hang_details;
        $report->sumo_signature = $this->_prepareSumoSignature($report->signature);

        if ($parse_dump) {
            $CrashReportDump = new CrashReportDump;
            $CrashReportDump->parseDump($report);
        }

        return $report;
    }
    
    /**
     * Prepare the reports for display.
     *
     * @param   array An array of report objects
     * @return  array An updated array of report objects
     */
    public function prepareCrashReports($reports)
    {
        foreach ($reports as $report) {
            $report = $this->prepareCrashReport($report, false);
        }
        return $reports;
    }
    
    /**
     * Prepare the meta data surrounding the report, including signatures 
     * and plugin names.
     *
     * @param   array An array of report objects
     * @return  array An array of report meta data.
     */
    public function prepareCrashReportsMeta($reports) 
    {
        $meta = $this->prepareCrashReportsMetaArray();
        foreach ($reports as $report) {
            if (
                property_exists($report, 'pluginname') && ! empty($report->pluginname) ||
                property_exists($report, 'pluginversion') && ! empty($report->pluginversion)
            ) {
                $meta['showPluginName'] = true;
            }

            if (property_exists($report, 'pluginfilename') && ! empty($report->pluginfilename)) {
                $meta['showPluginFilename'] = true;
            }

            if (isset($report->signature) && !empty($report->signature)) {
                array_push($meta['signatures'], $report->signature);
            }
        }

        $meta = array_unique($meta['signatures']);
        return $meta;
    }
    
    /**
     * Prepare the array used for report meta data.
     *
     * @return  array An array that is ready to accept report meta data.
     */
    public function prepareCrashReportsMetaArray()
    {
        return array(
            'showPluginFilename' => false,
            'showPluginName' => false,
            'signatures' => array()
        );
    }
    
    /**
     * Check the OOID to determine if this report is still valid.  If the timestamp
     * on the end of the OOID is correct and the timestamp is greater than or equal
     * to 3 years past the current date, then it is valid.
     *
     * @access  public 
     * @param   string  The $ooid for a crash
     * @return  bool    Return TRUE if valid; return FALSE if invalid
     */
    public function validateOOID ($ooid)
    {
        $crash_report_ttl = Kohana::config('application.crash_report_ttl');
		if ($ooid_timestamp = $this->parseOOIDTimestamp($ooid)) {
            if ($ooid_timestamp < (mktime(0, 0, 0, date("m"), date("d"), date("Y")-$crash_report_ttl))) {
                return false;
            } else {
                return true;
            }
		}
	
        // Can't determine just by looking at the OOID. Return TRUE.
        return true;
    }
    
}
