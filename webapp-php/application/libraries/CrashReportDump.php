<?php defined('SYSPATH') or die('No direct script access.');
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
	$basicKeys = array('product', 'version', 'uuid', 
			   'date_processed', 'uptime', 'build', 'os_name', 
			   'os_version', 'cpu_name', 'cpu_info', 'reason', 
			   'address', 'user_comments', 'dump');
	foreach ($basicKeys as $key) {
	    if (! isset($report->{$key})) {
		$report->{$key} = '';
	    }
	}
    }

    /**
     * Handels errors in the getJsonZ method.
     * Callers must rest $this->error_reading_file to FALSE
     * before use and then check it after IO calls.
     * @see getJsonZ
     * @see set_error_handler
     */
    public function handleError($errno, $errstr, $errfile, $errline)
    {
	Kohana::log('error', "$errstr $errfile line $errline");
	$this->error_reading_file = TRUE;
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
	$this->error_reading_file = FALSE;

	$eh = set_error_handler(array($this, 'handleError'));
	    $file = gzopen($uri, "r");
	    while($this->error_reading_file === FALSE &&
		  !feof($file)) {
		$output = $output . fgets($file, 4096);
	    }
	    gzclose ($file);
        set_error_handler($eh);
	if ($this->error_reading_file === TRUE) {
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