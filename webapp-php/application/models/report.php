<?php defined('SYSPATH') or die('No direct script access.');

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
      * @param  string uri for retrieving the crash dump
      * @return object Report data and dump data OR NULL
      */
    public function getByUUID($uuid, $crash_uri)
    {
	/* Note: 99% of our data comes from the processed crash dump
	         jsonz file. Only select columns that aren't in the json file
	         such as email which is SENSATIVE and should never appear in
                 the publically accessable jsonz file. Anything here will be 
                 merged into the model object + jsonz data */
        $report = $this->db->query(
            "/* soc.web report.dateProcessed */
                SELECT reports.email
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
	    $crash_report_json = $crashReportDump->getJsonZ($crash_uri);
    	    if( $crash_report_json !== FALSE ){
      	        $crashReportDump->populate($report, $crash_report_json);
		return $report;          
            } else {
		Kohana::log('info', "$uuid was processed, but $crash_uri doesn't exist (404)");
                return NULL;            
            }
    	}
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
}
