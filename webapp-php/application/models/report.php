<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Common model class managing the branches table.
 */
class Report_Model extends Model {

    /**
     * Perform overall initialization for the model.
     */
    public function __construct() {
        parent::__construct();
        $this->cache = new Cache();
    }

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

                    $frame = array(
                        'module_name'     => $module_name,
                        'frame_num'       => $frame_num,
                        'function'        => $function,
                        'instruction'     => $instruction,
                        // TODO:
                        'source'          => $source,
                        'source_line'     => $source_line,
                        'source_link'     => '',
                        'source_info'     => '',
                        'signature'       => "$module_name SIG",
                        'short_signature' => "$module_name SIG"
                    );

                    $report->threads[$thread_num][] = $frame;
                    break;
            }

        }

    }

}
