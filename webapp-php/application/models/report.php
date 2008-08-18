<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Common model class managing the branches table.
 */
class Report_Model extends Model {

    /**
     * Fetch a single report and associated dump data by UUID
     *
     * @param  string UUID by which to look up report
     * @return object Report data and dump data.
     */
    public function getByUUID($uuid) {

        $report = $this->db->query(
            'SELECT reports.*, dumps.data AS dump '.
            'FROM reports, dumps '.
            'WHERE reports.uuid=? AND dumps.report_id=reports.id', $uuid)->current();
        if (!$report) return FALSE;

        $this->_parseDump($report);
        
        return $report;
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

    /**
     * Parse the data from a dump into report attributes.
     *
     * @param string Text blob from the report dump.
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
                    $report->crashed_thread = $values[3];
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

                    /*  TODO:
                        # Settings for creating a link to a file in a given version control viewing 
                        # website. For example: 
                        #    {'cvs':{'cvs.mozilla.org/cvsroot':'http://bonsai.mozilla.org/cvsblame.cgi?file=%(file)s&rev=%(revision)s&mark=%(line)s#%(line)s'}} 
                        
                        if source is not None:
                          vcsinfo = source.split(":")
                          if len(vcsinfo) == 4:
                            (type, root, source_file, revision) = vcsinfo
                            self['source_filename'] = source_file
                            if type in config.vcsMappings:
                              if root in config.vcsMappings[type]:
                                self['source_link'] = config.vcsMappings[type][root] % \
                                                        {'file': source_file,
                                                         'revision': revision,
                                                         'line': source_line}
                          else:
                            self['source_filename'] = os.path.split(source)[1]

                        if self['source_filename'] is not None and self['source_line'] is not None:
                          self['source_info'] = self['source_filename'] + ":" + self['source_line']
                     */

                    $frame = array(
                        'module_name'     => $module_name,
                        'frame_num'       => $frame_num,
                        'function'        => $function,
                        'instruction'     => $instruction,
                        'signature'       => $signature,
                        'source'          => $source,
                        'source_line'     => $source_line,
                        'short_signature' => preg_replace('/\(.*\)/', '', $signature),
                        // TODO:
                        'source_filename' => '',
                        'source_link'     => '',
                        'source_info'     => ''
                    );

                    $report->threads[$thread_num][] = $frame;
                    break;
            }

        }

    }

}
