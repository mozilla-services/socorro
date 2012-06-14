<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
        $hang_details['is_hang'] = (isset($report->numhang) && $report->numhang > 0);
        $hang_details['is_plugin'] =  (isset($report->numplugin) && $report->numplugin > 0);
        $hang_details['is_content'] = (isset($report->numcontent) && $report->numcontent >0);
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
