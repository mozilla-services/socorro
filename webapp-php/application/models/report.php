<?php defined('SYSPATH') or die('No direct script access.');
//require_once dirname(__FILE__).'/../libraries/MY_CrashReportDump.php';

/**
 * Common model class managing the branches table.
 */
class Report_Model extends Model {

     /**
      * Checks to see if this crash report has been processed and if so
      * what was the date/time. If crash has not been processed yet
      * NULL is returned.
      *
      * @param  string UUID by which to look up report
      * @param  string root directory storing JSON dump files
      * @return object Report data and dump data OR NULL
      */
    public function getByUUID($uuid, $crashDir)
    {
        $report = $this->db->query(
            "/* soc.web report.dateProcessed */
            SELECT reports.date_processed
            FROM reports WHERE reports.uuid=? AND reports.success IS NOT NULL", $uuid)->current();
        if (!$report) {
            Kohana::log('info', "$uuid hasn't been processed");
            return NULL;
	} else {
	    $crashReportDump = new CrashReportDump;
	    $crashFile = $crashReportDump->crashFilename($crashDir, $uuid);
	    if( file_exists($crashFile) ){
  	        $crashReportDump->populate($report, $crashFile);
	        return $report;          
            } else {
	        Kohana::log('info', "$uuid was processed, but $crashFile doesn't exist");
                return NULL;            
            }
	}
    }

    /**
     * Lightweight way to see if a crash report has been processed
     * @param  string uuid of the crash
     * @param  string root directory storing JSON dump files
     * @return boolean TRUE if crash dump exists FALSE if it is still pending processing
     */
    public function exists($uuid, $crashDir)
    {
        $crashReportDump = new CrashReportDump;
        $crashFile = $crashReportDump->crashFilename($crashDir, $uuid);
        return file_exists($crashFile);
    }
}
