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
 * Responsible for knowing about how to manipulate an indiviudal crash
 * from the reports table.
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
     * Parses an OOID from a string. Doens't check in database for it's existance
     * - about:crashes style id
     * - uuid
     * - simple search
     * @param string input
     * @param string uuid OR FALSE
     */
    public function parseOOID($input)
    {
        $ooid = FALSE;
        if ($input) {
            $matches = array();
            $prefix = Kohana::config('application.dumpIDPrefix');
            if ( preg_match('/^('.$prefix.')?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/', $input, $matches) ) {
                $ooid = $matches[2];
            }
        }
        return $ooid;
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
        if (property_exists($report, 'signature') && (is_null($report->signature)) ||
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

        $meta['signatures'] = array_unique($meta['signatures']);
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

}
