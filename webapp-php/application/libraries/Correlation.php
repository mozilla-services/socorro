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

require_once Kohana::find_file('libraries', 'ErrorHandler', true, 'php');

/**
 * Responsible for loading Correlation reports from people.mozilla.com.
 * These reports are long text files. We retrieve them, break them up
 * by platform, and cache the results by signature.
 *
 * This data is used via AJAX requests from /report/index/{UUID}
 *
 * For our major release, there is *a lot* of correlatin data. To
 * keep things speedy and not overwhelm the caching service, we
 * only load correlation.max_file_size worth of data from
 * each section of a text file.
 *
 * @author Austin King <aking@mozilla.com>
 */
class Correlation
{
    /** Tracks which platform we're processing */
    public $current_platform;
    /** Tracks which signature we're processing */
    public $current_signature;

    /**
     * Wrapper which opens text files
     *
     * @param string $uri Url or filename which contains a Correlation report
     *
     * @see _get
     * @return The Correlation report organized by signature and platforms
     */
    function getTxt($uri)
    {
        return $this->_get($uri, 'fopen', 'fclose');
    }

    /**
     * Wrapper which opens gzip compressed text files
     *
     * @param string $uri Url or filename which contains a Correlation report
     *
     * @see _get
     * @return The Correlation report organized by signature and platforms
     */
    function getGz($uri)
    {
        return $this->_get($uri, 'gzopen', 'gzclose');
    }

    /**
     * Reads text from a gzip compressed resource with special attention to 'Platform Sections'.
     * A platform section is a line like ^Windows$. Each time a platform section is encountered
     * the reader counter is reset.
     *
     * @param string   $uri      Url or remote file
     * @param callback $open_fn  callback suitable for opening a file or stream
     * @param callback $close_fn callback suitable for closing a file or stream
     *
     * @return array The Correlation report organized by signature and platforms
     *
     * Example: {'nsAppShell::ProcessNextNativeEvent(int)' =>
     *                    {'Mac OS X' => ['99% (6026/6058) vs.   6% (6245/102490) overlapp32.dll',
     *                                    '66% (4010/6058) vs.  20% (20236/102490) MSCTFIME.IME'] }}
     *
     */
    function _get($uri, $open_fn, $close_fn)
    {
        $platforms = array('None', 'Linux', 'Mac OS X', 'Windows', 'Windows NT');
        $platforms_seen_count = 0;
        $this->sig2modules = array();
        $err = new ErrorHandler;

        $eh = set_error_handler(array($err, 'handleError'));
        $file = call_user_func($open_fn, $uri, "r"); //gzopen($uri, "r");

        // Stop reading the file once you've seen all the platforms AND you've read the max from each
        while ($err->error_reading_file === false &&
              !feof($file)) {
            $line = fgets($file, 4096);
            $platform_line = false;

            $ch = substr($line, 0, 1);
            if ($ch == 'N' || $ch == 'L' || $ch == 'M' || $ch == 'W') {
                    //cache so we don't check twice
                    $platform_line = true;
                    $platforms_seen_count++;
            }

            if ($platform_line) {
                $this->parsePlatform($line);
            } else {
                $this->parseText($line);
            }
        }
        if ($file !== false) {
            call_user_func($close_fn, $file);
        }
        set_error_handler($eh);
        $results = array();

        foreach ($this->sig2modules as $sig => $oses) {
            $results[$sig] = array();
            foreach ($oses as $os => $reasons) {

                $results[$sig][$os] = array();
                $crashiest = null;
                foreach ($reasons as $reason => $details) {
                    $details['crash_reason'] = $reason;
                    if (is_null($crashiest)) {
                        $crashiest = $details;
                    } else {
                        if ($crashiest['count'] < $reason['count']) {
                            $crashiest = $details;
                        }
                    }
                }
                // replace the list of reasons with the single most popular crash reason
                // Example: EXCEPTION_ACCESS_VIOLATION (2724 crashes)
                $results[$sig][$os] = $crashiest;
            }
        }
        if ($err->error_reading_file === true) {
            return false;
        } else {
            return $results;
        }
    }

    /**
     * Handle a line of text that should be a platform.
     * Platforms create 'sections' of a long text document. We
     * only read 2MB or whatever passed this line.
     *
     * @param string $line A String such as 'Mac OS X'
     *
     * @return void
     */
    public function parsePlatform($line)
    {
        $this->current_platform = trim($line);
        $this->current_signature = null;
    }

    /**
     * Handle a line of text from the correlation report
     *
     * @param string $line A String that is either blank,
     *                     a signature line, or the body of a report
     *
     * @return void
     */
    public function parseText($line)
    {
        $l = trim($line);
        if ($this->isSignature($l)) {
            $this->parseSignatureLine($l);
        } else if ($l === '') {
            $this->current_signature = null;
        } else {
            $this->parseCorrelation($l);
        }
    }

    /**
     * Checks to see if a given line is a signature.
     * This is largely dependent on the state the parser
     *
     * @param string $line A line from a correlation report
     *
     * @return Boolean
     */
    public function isSignature($line)
    {
        return is_null($this->current_signature) &&
               $line !== '';
    }

    /**
     * Handle a line of text which contains a Signature, Crash Reason, and other data.
     * Updates parser state.
     *
     * @param string $line A Line from the report which contains
     *                     a crash signature.
     *
     * @return void
     */
    public function parseSignatureLine($line)
    {
        list($this->current_signature, $this->current_reason) = $this->parseSignature($line);
    }

    /**
     * Parses the Crashing Signature of a "signature line" of a report
     * Updates parser state. It will skip to the last signature present.
     *
     * @param string $line A signature line from a report
     *
     * @return - array with 2 elements: The Signature and The Crash Reason
     */
    public function parseSignature($line)
    {
        if (strpos($line, '|') === false) {
            return array($line, $this->_makeReason('UNKNOWN', -1));
        } else {
            $parts = explode('|', $line);
            // Grab the 2nd one from the right, it seems these reports show their SkipList
            $i = count($parts) - 2;
            $r = end($parts);
            $reason = '';
            if (strpos($r, ' ') === false) {
                $reason = $this->_makeReason(trim($r), -1);
            } else {
                //EXCEPTION_ACCESS_VIOLATION (2724 crashes)
                $reasonParts = explode(' ', $r);
                $reasonCount = -1;
                if (substr($reasonParts[1], 0, 1)  == '(') {
                    $reasonCountLength = strlen($reasonParts[1]) - 1;
                    $reasonCount = intval(substr($reasonParts[1], 1, $reasonCountLength));
                }
                $reason = $this->_makeReason(trim($reasonParts[0]), $reasonCount);
            }
            return array(trim($parts[$i]), $reason);
        }
    }

    /**
     * Helper method to make an array that contains the
     * reason the crash happened and the total count of crashes
     *
     * @param string  $crash_reason A reason Example:
     *                              EXCEPTION_ACCESS_VIOLATION
     * @param integer $count        The total count
     *
     * @return array with keys for 'reason' and 'count'
     */
    private function _makeReason($crash_reason, $count)
    {
        return array('reason' => $crash_reason,
                     'count' => $count);
    }

    /**
     * Handels a line from the body of a correlation report
     * and updates the parsers state.
     *
     * @param string $line A line from the body of a report
     *
     * @return void
     */
    public function parseCorrelation($line)
    {
        $sig = $this->current_signature;
        //$line trim by callee
        if (! array_key_exists($sig, $this->sig2modules)) {
            $this->sig2modules[$sig] = array();
        }
        if (! array_key_exists($this->current_platform, $this->sig2modules[$sig])) {
            $this->sig2modules[$sig][$this->current_platform] = array();
        }
        $crash_reason = $this->current_reason['reason'];
        if (! array_key_exists($crash_reason, $this->sig2modules[$sig][$this->current_platform])) {
            $this->sig2modules[$sig][$this->current_platform][$crash_reason] = array(
                'count' => $this->current_reason['count'],
                'correlations' => array());
        }
        array_push($this->sig2modules[$sig][$this->current_platform][$crash_reason]['correlations'], $line);
    }

    /**
     * Fragile mapping between OS names in dbaron's reports
     *
     * @param int $win_count Total crash count for Windows
     * @param int $mac_count Total crash count for Mac
     * @param int $lin_count Total crash count for Linux
     *
     * @return string OS name for use with /correlation/ajax
     */
    public static function correlationOsName($win_count, $mac_count, $lin_count)
    {
        if ($win_count >= $mac_count && $win_count >= $lin_count) {
            return 'Windows NT';
        } elseif ($mac_count >= $win_count && $mac_count >= $lin_count) {
            return 'Mac OS X';
        } else {
            return 'Linux';
        }
    }
}
?>
