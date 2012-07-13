<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

require_once Kohana::find_file('libraries', 'Correlation', true, 'php');

/**
 * Non-visual controller for adding Correlation reports to a page.
 *
 * @author      Austin King <aking@mozilla.com>
 */
class Correlation_Controller extends Controller
{

    public function __construct()
    {
        parent::__construct();
        $this->cache = new Cache(Kohana::config('correlation.caching'));
    }

    /**
     * Gets the full report name given the type code in ajax path.
     *
     * @param string $type The short name used in Ajax urls for the report
     *               type
     *
     * @return string, boolean Full name of report or the boolean false if
     *               there is no valid mapping.
     */
    private function _reportType($type)
    {
        $types = array('cpu'           => 'core-counts',
                       'addon'         => 'interesting-addons',
                       'addonversion'  => 'interesting-addons-with-versions',
                       'module'        => 'interesting-modules',
                       'moduleversion' => 'interesting-modules-with-versions');
        if (array_key_exists($type, $types)) {
            return $types[$type];
        } else {
            return false;
        }
    }

    /**
     * Handel an AJAX request based on various parameters.
     * Respond with an HTML fragment suitable for loading in the page.
     *
     * @param string $type      Must be a valid short name for reports.
     *                          (see _reportType function)
     * @param string $product   A Product name
     * @param string $version   A Product Version
     * @param string $platform  A Platform, must be one of Mac OS X, Windows,
                                Windows NT, Linux
     * @param string $signature A top crashing signature
     */
    public function ajax($type = null, $product = null, $version = null, $platform = null, $signature = null)
    {
    set_time_limit(Kohana::config('correlation.file_processing_timeout'));
        $report_name = $this->_reportType($type);
        if (false !== $report_name) {
            list($status, $data) = $this->_getCorrelations($report_name, $product, $version, $platform, $signature);
            if (true === $status) {
                $this->_ajax($type, $product, $version, $platform, $signature, $data);
            } else {
                $this->_noSignatureData($data);
            }
        } else {
            $this->_noSignatureData("ERROR: Unknown report type $type");
        }
    }

    /**
     * Handle an AJAX request based on various parameters. Respond with an
     * HTML fragment suitable for loading in the page.
     *
     * $.post('/reporter/correlation/bulk_ajax/cpu/Firefox/3.6/Windows%20NT/',
     *            {'signatures[]': ['UserCallWinProcCheckWow', '_PR_MD_SEND']});
     *
     * @param string $type    Must be a valid short name for reports.
     *                        (see _reportType function)
     * @param string $product A Product name
     * @param string $version A Product Version
     */
    public function bulk_ajax($type = null, $product = null, $version = null)
    {
        $osnames = $this->input->post('osnames');
        $signatures = $this->input->post('signatures');

        if ($signatures && $osnames) {
            if (count($osnames) !== count($signatures)) {
                $err = "ERROR: OS / Signature list mismatch";
                return $this->_noSignatureData($err);
            }

            set_time_limit(Kohana::config('correlation.file_processing_timeout'));

            $report_name = $this->_reportType($type);
            if (false !== $report_name) {
                $response = array();
                for ($i = 0; $i < count($signatures); $i++) {
                    $platform = $osnames[$i];
                    $signature = $signatures[$i];
                    list($status, $data) = $this->_getCorrelations($report_name, $product, $version, $platform, $signature);
                    $item = array('rank' => $i + 1, 'signature' => $signature);
                    if (true === $status) {
                        if (array_key_exists($platform, $data)) {
                $item['correlation'] = View::factory('correlation/correlation', array(
                    'details' => $data[$platform]
                            ))->render();
                        } else {
                            $err = "No Data for $platform when correlating $product $version $signature ";
                            $item['correlation'] = $err;
                        }
                    } else {
                        $item['correlation'] = $data; // has error message
                    }
                    array_push($response, $item);
                }// end for
                $this->auto_render = false;
                echo json_encode($response);
            } else {
                $this->_noSignatureData("ERROR: Unknown report type $type");
            }
        } else {
            $err = "ERROR: Expected POST with a list of signatures";
            $this->_noSignatureData($err);
        }
    }

    /**
     * Loads the correlation reports for the given prod/version/os/signature.
     * These may not exist, or not exist for the given signature.
     *
     * @param string $report_name Name of the report
     * @param string $product     A Product name
     * @param string $version     A Product Version
     * @param string $platform    An Operating System
     * @param string $signature   A top crash signature
     *
     * @return array An array of status and data. Status is a boolean. Data is
     *               either a string or the corrlation data
     *               Example: [false, 'ERROR: No data']
     */
    private function _getCorrelations($report_name, $product, $version, $platform, $signature)
    {
        $day = //'20100224';
               date('Ymd'); //
        $correlation = new Correlation;

        $cache_key = $this->_getCacheKey($day, $product, $version, $report_name, $signature);
        $data = $this->cache->get($cache_key);
        if ($data) {
            Kohana::log('debug', "CACHE HIT " . $cache_key);
            return array(true, $data);
        } else if ($this->cache->get($this->_getGeneralCacheKey($day, $product, $version, $report_name)) === true) {
            $err = "Loaded Correlation Data, but none available for this signature <code>$signature</code>";
            return array(false, $err);
        } else {
            $report = Kohana::config('correlation.path') . "${day}/${day}_${product}_${version}-${report_name}";

            // Depending on file size, the report will be text or
            // gzipped text. Try both
            $data = $correlation->getTxt($report . '.txt');
            if ($data === false) {
                $data = $correlation->getGz($report . '.txt.gz');
            }

            //Record general access
            $this->cache->set($this->_getGeneralCacheKey($day, $product, $version, $report_name), true);

            if ($data !== false) {
                if (array_key_exists($signature, $data)) {
                    $results = array(true, $data[$signature]);
                } else {
                    $err = "Loaded Correlation Data, but non available for this signature <code>$signature</code>";
                    $results = array(false, $err);
                }

                foreach ($data as $cur_sig => $sig_data) {
                    $cache_key = $this->_getCacheKey($day, $product, $version, $report_name, $cur_sig);
                    $this->cache->set($cache_key, $sig_data);
                }

                return $results;
            }
            $err = "ERROR: No reports generated on $day for $product ${version}. Looked at ${report}.txt and ${report}.txt.gz";
            return array(false, $err);
        }
    }

    /**
     * Creates a cache key for a signature
     *
     * @param string $day         The day we are interested in.
     *                            Example: '20100218' for Feb 18th, 2010
     * @param string $product     A Product name
     * @param string $version     A product Version
     * @param string $report_name The name of a reports dbaron generates.
     *                            Based on his filenames
     *                            Examples: 'core-counts', 'interesting-addons'
     * @param string $signature   A top crashing signature
     *
     * @return string The formatted cache key
     */
    private function _getCacheKey($day, $product, $version, $report_name, $signature)
    {
        return "correlate_" . md5("${day}_${product}_${version}_${report_name}_${signature}");
    }

    /**
     * Creates a general cache key for recording that we've already loaded and parsed
     * the correlation report. Useful for knowing if we won't find a signature even
     * if we try again.
     *
     * @param string $day         The day we are interested in.
     *                            Example: '20100218' for Feb 18th, 2010
     * @param string $product     A Product name
     * @param string $version     A product Version
     * @param string $report_name The name of a reports dbaron generates.
     *                            Based on his filenames not including date.
     *                            Examples: 'core-counts', 'interesting-addons'
     *
     * @return string The formatted cache key
     */
    private function _getGeneralCacheKey($day, $product, $version, $report_name)
    {
        return "correlate_${day}_${product}_${version}_${report_name}";
    }

    /**
     * Formats the HMLT for corrlation data
     *
     * @param array $correlation_details Associative Array with
     *                                   crash_reason, count, and correlations
     *
     * @return string The HTML formatted correlation for display

    private function _formatCorrelationData($correlation_details)
    {
        $crash_reason = $correlation_details['crash_reason'];
        $count = $correlation_details['count'];

        $correlations = join("\n", $correlation_details['correlations']);
        return "<div class='correlation'><h3>${crash_reason} (${count})</h3><pre>${correlations}</pre></div>";
    }
*/
    /**
     * Outputs the HTML Response when we have data for a successful
     * ajax request.
     *
     * @param string $type      Must be a valid short name for reports.
     *                          (see _reportType function)
     * @param string $product   A Product name
     * @param string $version   A Product Version
     * @param string $platform  A Platform, must be one of Mac OS X, Windows,
                                Windows NT, Linux
     * @param string $signature A top crashing signature
     * @param array  $data      An array of Platforms which are a key
     *                          into an strings which contains the report
     *             Example: { 'Mac OS X' => ['99% (6026/6058) vs.   6% (6245/102490) overlapp32.dll',
     *                                       '66% (4010/6058) vs.  20% (20236/102490) MSCTFIME.IME'] }
     */
    private function _ajax($type, $product, $version, $platform, $signature, $data)
    {
        $this->auto_render = false;
        if ($data !== false) {
            if (array_key_exists($platform, $data)) {
        $item['correlation'] = View::factory('correlation/correlation', array(
            'details' => $data[$platform]
                ))->render(TRUE);
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
     *
     * @param string $message The Message to display
     */
    private function _noSignatureData($message)
    {
        $this->auto_render = false;
        echo $message;
    }
}
?>
