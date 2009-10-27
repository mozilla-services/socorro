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
                FROM reports 
                WHERE reports.uuid=? 
                AND reports.success 
                IS NOT NULL
            ", $uuid)->current();
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
     *
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

    /**
     * Determine whether or not this crash report is available.
     *
     * @access  public
     * @param   string  The $uuid for this report
     * @return  bool    Return TRUE if available; return FALSE if unavailable 
     *
     */
    public function isReportAvailable ($uuid)
    {
        $crashDirs = Kohana::config('application.dumpPaths');
        foreach ($crashDirs as $crashDir) {
            if ($this->exists($uuid, $crashDir)) {
                if ($report = $this->getByUUID($uuid, $crashDir)) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * Check the UUID to determine if this report is still valid.
     *
     * @access  public 
     * @param   string  The $uuid for this report
     * @return  bool    Return TRUE if valid; return FALSE if invalid
     */
    public function isReportValid ($uuid)
    {
        $uuid_chunks = str_split($uuid, 6);
        if (isset($uuid_chunks[5]) && is_numeric($uuid_chunks[5])) {
            $uuid_date = str_split($uuid_chunks[5], 2);
            if (isset($uuid_date[0]) && isset($uuid_date[1]) && isset($uuid_date[2])) {
                $uuid_timestamp = mktime(0, 0, 0, $uuid_date[1], $uuid_date[2], $uuid_date[0]);
                if ($uuid_timestamp < (mktime(0, 0, 0, date("m"), date("d"), date("Y")-3))) {
                    return false;
                } else {
                    return true;
                }
            }
        }

        // Can't determine just by looking at the UUID. Return TRUE.
        return true;
    }

    /**
     * Determine whether or not this signature exists within the `reports` table.
     *
     * @param   ?       The signature for the report
     * @return  bool    Return TRUE if exists; return FALSE if does not exist
     */
    public function sig_exists($signature)
    {
        $rs = $this->db->query(
                "/* soc.web report sig exists */
                    SELECT signature 
                    FROM reports 
                    WHERE signature = ?
                    LIMIT 1
                ", $signature)->current();
        if ($rs) {
	        return TRUE;
        } else {
	        return FALSE;
	    }
    }

    /* */
}
