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
 * Knows about the on disk format of crash report dumps.
 * Dependency: This code is coupled with python processor code
 *   changing the name, format, or location of crash dumps
 *   should be done in this file and in that sub-system
 */
class CrashReportDump {
    /**
     * Populates a crash report with the contents
     * of a JSON encoded crash report dump.
     *
     * The report object may already have some properties set
     * from the database, such as date_processed. The bulk of
     * the properties come from the gzip compressed JSON encoded
     * crash dump file on the filesystem.
     *
     * @param stdClass report object
     * @param string JSON encoded processed crash report
     * @return void report will be altered
     */
    public function populate($report, $json) {
	$data = json_decode($json);

	foreach ($data as $key => $val) {
	    $report->{$key} = $val;
	}
	$this->_parseDump($report); 
	//Bulletproofing against bad JSON files
	$basicKeys = array('signature', 'product', 'version', 'uuid', 
			   'date_processed', 'uptime', 'build', 'os_name', 
			   'os_version', 'cpu_name', 'cpu_info', 'reason', 
			   'address', 'user_comments', 'dump', 'processor_notes');
	foreach ($basicKeys as $key) {
	    if (! isset($report->{$key})) {
		$report->{$key} = '';
	    }
	}
        if (is_array($report->processor_notes)) {
            $report->processor_notes = "\n".join($report->processor_notes);
        }
    }

   /**
    * The processed crash dump metadata is stored in
    * a gzipped JSON encoded file. This method retreieves
    * it and de-compresses it
    *
    * @param string A valid uri to the crash dump
    * @return string with JSON data or FALSE if their is a issue getting JSON
    */
    public function getJsonZ($uri)
    {
        $output="";
	$err = new ErrorHandler;

	$eh = set_error_handler(array($err, 'handleError'));
	    $file = gzopen($uri, "r");
	    while($err->error_reading_file === FALSE &&
		  !feof($file)) {
		$output = $output . fgets($file, 4096);
	    }
	    gzclose ($file);
        set_error_handler($eh);
	if ($err->error_reading_file === TRUE) {
	    Kohana::log('alert', "Could not load $uri");
	    return FALSE;
	} else {
	    return $output; 
	}
    }

    /**
     * Parses the 'dump' property which is a string
     * into the module, and frame stacks, etc.
     *
     * @param stdClass report object with a property 'dump' which is a 
     *        Text blob from the report dump.
     */
    public function _parseDump($report) {
        
        $dump_lines = explode("\n", $report->dump);
        $report->modules = array();
        $report->threads = array();

        foreach ($dump_lines as $line) {
            
            if ($line == '') continue;
            $values = explode('|', $line);

            switch($values[0]) {

                case 'OS':
                    $report->os_name    = $values[1];
                    $report->os_version = $values[2];
                    break;

                case 'CPU':
                    $report->cpu_name = $values[1];
                    $report->cpu_info = $values[2];
                    break;

                case 'Crash':
                    $report->reason         = $values[1];
                    $report->address        = $values[2];
                    $report->crashed_thread = intval($values[3]);
                    break;

                case 'Module':
                    $report->modules[] = array(
                        'filename'       => $values[1],
                        'debug_id'       => $values[4],
                        'module_version' => $values[2],
                        'debug_filename' => $values[3]
                    );
                    break;

                default:
                    list($thread_num, $frame_num, $module_name, $function, 
                        $source, $source_line, $instruction) = $values;

                    if (!isset($report->threads[$thread_num])) {
                        $report->threads[$thread_num] = array();
                    }
                    
                    $signature = $this->_makeSignature(
                        $module_name, $function, $source, $source_line, $instruction
                    );

                    $frame = array(
                        'module_name'     => $module_name,
                        'frame_num'       => $frame_num,
                        'function'        => $function,
                        'instruction'     => $instruction,
                        'signature'       => $signature,
                        'source'          => $source,
                        'source_line'     => $source_line,
                        'short_signature' => preg_replace('/\(.*\)/', '', $signature),
                        'source_filename' => '',
                        'source_link'     => '',
                        'source_info'     => ''
                    );

                    if ($source) {
                        $vcsinfo = explode(':', $source);
                        if (count($vcsinfo) == 4) {
                            list($type, $root, $source_file, $revision) = $vcsinfo;

                            $frame['source_filename'] = $source_file;
                            
                            // Attempt to build a VCS web link from app config 
                            // settings and a ghetto simulation of Python 
                            // string templates.
                            $vcs_mappings = Kohana::config('codebases.vcsMappings');
                            if (isset($vcs_mappings[$type][$root])) {
                                $link = $vcs_mappings[$type][$root];
                                $ns = array(
                                    'file'     => $source_file,
                                    'revision' => $revision,
                                    'line'     => $frame['source_line']
                                );
                                foreach ($ns as $name => $val) {
                                    $link = str_replace( "%($name)s", $val, $link );
                                }
                                $frame['source_link'] = $link;
                            }

                        } else {
                            $path_parts = explode('/', $source);
                            $frame['source_filename'] = array_pop($path_parts);
                        }

                    }
                    if ($frame['source_filename'] && $frame['source_line']) {
                        $frame['source_info'] = $frame['source_filename'] . ':' . $frame['source_line'];
                    }

                    $report->threads[$thread_num][] = $frame;
                    break;
            }
        }
    }

    /**
     * Given the details of a frame, build a signature for display.
     */
    public function _makeSignature($module_name, $function, $source, $source_line, $instruction) {
        if ($function) {
            // Remove spaces before all stars, ampersands, and commas
            $function = preg_replace('/ (?=[\*&,])/', '', $function);
            // Ensure a space after commas
            $function = preg_replace('/(?<=,)(?! )/', '', $function);
            return $function;
        }

        if ($source && $source_line) {
            //filename_re = re.compile('[/\\\\]([^/\\\\]+)$')
            //filename = filename_re.search(source)
            //if filename is not None:
            //  source = filename.group(1)
            
            return "$source#$source_line";
        }
    
        if ($module_name) {
            return "$module_name@$instruction";
        }

        return "@$instruction";
    }

}