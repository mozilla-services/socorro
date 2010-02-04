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

require_once(Kohana::find_file('libraries', 'ErrorHandler', TRUE, 'php'));

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
 * @author     	Austin King <aking@mozilla.com>
 */
class Correlation
{
    /** Tracks which platform we're processing */
    public $current_platform;
    /** Tracks which signature we're processing */
    public $current_signature;

    /**
     * Wrapper which opens text files
     * @param - url or filename which contains a Correlation report
     * @param - The maximum data in megabytes we should read for each 
     *          platform section. -1 for unlimited.
     * @see _get
     * @return The Correlation report organized by signature and platforms
     */
    function getTxt($uri, $max_read = -1)
    {
	return $this->_get($uri, $max_read, 'fopen', 'fclose');
    }

    /**
     * Wrapper which opens gzip compressed text files
     * @param - url or filename which contains a Correlation report
     * @param - The maximum data in megabytes we should read for each 
     *          platform section. -1 for unlimited.
     * @see _get
     * @return The Correlation report organized by signature and platforms
     */
    function getGz($uri, $max_read = -1)
    {
	return $this->_get($uri, $max_read, 'gzopen', 'gzclose');
    }

    /**
     * Reads text from a gzip compressed resource with special attention to 'Platform Sections'.
     * A platform section is a line like ^Windows$. Each time a platform section is encountered
     * the reader counter is reset.
     *
     * @param - locale or remote file
     * @param - The maximum data in megabytes we should read for each 
     *          platform section. -1 for unlimited.
     * @param - callback suitable for opening a file or stream
     * @param - callback suitable for closing a file or stream
     * @return The Correlation report organized by signature and platforms
     *
     * Example: {'nsAppShell::ProcessNextNativeEvent(int)' => 
     *                    {'Mac OS X' => ['99% (6026/6058) vs.   6% (6245/102490) overlapp32.dll',
     *                                    '66% (4010/6058) vs.  20% (20236/102490) MSCTFIME.IME'] }}
     * 
     */
    function _get($uri, $max_read, $open_fn, $close_fn)
    {
	$platforms = array('None', 'Linux', 'Mac OS X', 'Windows', 'Windows NT');
	$platforms_seen_count = 0;
	$this->sig2modules = array();
	$err = new ErrorHandler;

	$eh = set_error_handler(array($err, 'handleError'));
	$file = call_user_func($open_fn, $uri, "r"); //gzopen($uri, "r");
	$amount_read = 0;

	#Kohana::log('info', "Reading with $open_fn");
	#Kohana::log('info', "file is " . var_dump($file) . Kohana::debug($file));

	// Stop reading the file once you've seen all the platforms AND you've read the max from each
	while($err->error_reading_file === FALSE &&
	      !feof($file) &&
	      ($platforms_seen_count < count($platforms) || $amount_read < $max_read)) {
	    $line = fgets($file, 4096);
	    $platform_line = FALSE;

	    //if (in_array(trim($line), $platforms)) {
	    $ch = substr($line, 0, 1);
	    if ($ch == 'N' || $ch == 'L' || $ch == 'M' || $ch == 'W') {
		    //cache so we don't check twice
		    $platform_line = TRUE;
		    $amount_read = 0;
		    $platforms_seen_count++;
		    //}
	    }

	    if ($max_read == -1 || $amount_read < $max_read) {
		if ($platform_line) {
		    $this->parsePlatform($line);
		} else {
		    $this->parseText($line);
		}

		$amount_read += strlen($line);;
	    }
	}
	if ($file !== FALSE) {
	    call_user_func($close_fn, $file);
	}
        set_error_handler($eh);
	if ($err->error_reading_file === TRUE) {
	    return FALSE;
	} else {
	    return $this->sig2modules; 
	}
    }

    /**
     * Handle a line of text that should be a platform.
     * Platforms create 'sections' of a long text document. We
     * only read 2MB or whatever passed this line.
     * @param A String such as 'Mac OS X'
     */
    public function parsePlatform($line)
    {
	$this->current_platform = trim($line);
	$this->current_signature = NULL;
    }

    /**
     * Handle a line of text from the correlation report
     * @param A String that is either blank, a signature line, or the body of a report
     */
    public function parseText($line)
    {
	$l = trim($line);
	if ($this->isSignature($l)) {
	    $this->parseSignatureLine($l);
	} else if ($l === '') {
	    $this->current_signature = NULL;
	} else {
	    $this->parseCorrelation($l);
	}
    }

    /**
     * Checks to see if a given line is a signature.
     * This is largely dependent on the state the parser
     *
     * @param - A String
     * @return Boolean
     */
    public function isSignature($line)
    {
	return is_null($this->current_signature) &&
	       $line !== '';
    }

    /**
     * Handle a line of text which contains a Signature and other data.
     * Updates parser state.
     * @param A String that is a signature line
     */
    public function parseSignatureLine($line) 
    {
	$this->current_signature = $this->parseSignature($line);
    }

    /**
     * Parses the Crashing Signature of a "signature line" of a report
     * Updates parser state. It will skip to the last signature present.
     * 
     * @param A String that is a signature line
     * @return - The Signature
     */
    public function parseSignature($line)
    {
	if (strpos($line, '|') === false) {
	    return $line;
	} else {
	    $parts = explode('|', $line);
	    // Grab the 2nd one from the right, it seems these reports show their SkipList
	    $i = count($parts) - 2;

	    return trim($parts[$i]);
	}
    }

    /**
     * Handels a line from the body of a correlation report
     * and updates the parsers state.
     *
     * @param - A String that is the body of a report
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
	array_push($this->sig2modules[$sig][$this->current_platform], $line);
    }
}
?>