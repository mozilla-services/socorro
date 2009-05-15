<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Knows about the on disk format of crash report dumps.
 * Dependency: This code is coupled with python processor code
 *   changing the name, format, or location of crash dumps
 *   should be done in this file and in that sub-system
 */
class CrashReportDump {
    /**
     * Creates a filename and path for a crash report
     * based on the dump directory and the UUID of a crash.
     * @param  string dumps directory
     * @param  string uuid of the crash
     * @return a filesystem full filename
     */
    public function crashFilename($dir, $uuid)
    {
        if (strlen($uuid) > 4) {
	    return implode("/", array($dir, substr($uuid, 0, 2), substr($uuid, 2, 2), $uuid)) . ".jsonz";
        } else {
	  throw new Exception("Bad arguments to crashFilename uuid too short $uuid");
	}
    }

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
     * @param string filename of gzip JSON file
     * @return void report will be altered
     */
    public function populate($report, $filename) {
        if (file_exists($filename) && is_readable($filename) ) {	    
    	    $data = json_decode($this->_readFile($filename));
            foreach ($data as $key => $val) {
  	        $report->{$key} = $val;
	    }
            $this->_parseDump($report); 
	    //Bulletproofing against bad JSON files
            $basicKeys = array('signature', 'product', 'version', 'uuid', 
			       'date_processed', 'uptime', 'build', 'os_name', 
			       'os_version', 'cpu_name', 'cpu_info', 'reason', 
			       'address', 'user_comments', 'dump');
	    foreach ($basicKeys as $key) {
                if (! isset($report->{$key})) {
	            $report->{$key} = '';
	        }
	    }
        } else {
  	    throw new Exception("Crash Dump file not found or not readable $filename");
        }
    }

    private function _readFile($filename)
    {
        $output="";
        $file = gzopen($filename, "r");
        while(!feof($file)) {
            $output = $output . fgets($file, 4096);
        }
        gzclose ($file);
        return $output; 
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
                            $vcs_mappings = Kohana::config('application.vcsMappings');
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