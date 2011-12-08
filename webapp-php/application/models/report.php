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


	    $crashReportDump = new CrashReportDump;
	    $crash_report_json = $crashReportDump->getJsonZ($crash_uri);
	    if($crash_report_json === false){
                Kohana::log('info', "$uuid could not fetch processed JSON");
                return false;
        } else if ($crash_report_json === true) {
                Kohana::log('info', "$uuid was reported but not processed; a priority job has been scheduled.");
                return true;
        } else if( !is_bool($crash_report_json) ){
			/* Note: 99% of our data comes from the processed crash dump
			         jsonz file. Only select columns that aren't in the json file
			         such as email which is SENSITIVE and should never appear in
		                 the publically accessable jsonz file. Anything here will be
		                 merged into the model object + jsonz data */
		        // Added addons_checked since that's not in the jsonz - bug 590245
		        $report = $this->db->query(
		            "/* soc.web report.dateProcessed */
		                SELECT reports.email, reports.url, reports.addons_checked,
			            ( SELECT reports_duplicates.duplicate_of FROM reports_duplicates WHERE reports_duplicates.uuid = reports.uuid) as duplicate_of
		                FROM reports
		                WHERE reports.uuid=?
		                AND reports.success
		                IS NOT NULL
		            ", $uuid)->current();
	            if(!$report) {
                        Kohana::log('info', "$uuid processed crash exists in HBase but does not exist in the reports table");
                        return false;
	            }

      	        $crashReportDump->populate($report, $crash_report_json);
		        return $report;
        } else {
		Kohana::log('info', "$uuid doesn't exist (404)");
                return NULL;
        }

    }

	/**
	 * Determine whether or not the raw dumps are still on the system and return the URLs
	 * by which they may be downloaded.  UUID must contain a timestamp that is within the given
	 * acceptable timeframe found in Kohana::config('application.raw_dump_availability').
	 *
	 * @param 	string	The $uuid for the dump
	 * @return  array|bool 	Return an array containing the dump and json urls for download; else
	 *					return false if unavailable
	 */
	public function formatRawDumpURLs ($uuid) {
		if ($uuid_timestamp = $this->uuidTimestamp($uuid)) {
			if ($uuid_timestamp > (time() - Kohana::config('application.raw_dump_availability'))) {
				return array(
					Kohana::config('application.raw_dump_url') . $uuid . '.dump',
					Kohana::config('application.raw_dump_url') . $uuid . '.json',
				);
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
		if ($uuid_timestamp = $this->uuidTimestamp($uuid)) {
            if ($uuid_timestamp < (mktime(0, 0, 0, date("m"), date("d"), date("Y")-3))) {
                return false;
            } else {
                return true;
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

    /**
     * Determine the timestamp for this report by the given UUID.
     *
     * @access  public
     * @param   string  The $uuid for this report
     * @return  int    	The timestamp for this report.
     */
    public function uuidTimestamp ($uuid)
    {
        $uuid_chunks = str_split($uuid, 6);
        if (isset($uuid_chunks[5]) && is_numeric($uuid_chunks[5])) {
            $uuid_date = str_split($uuid_chunks[5], 2);
            if (isset($uuid_date[0]) && isset($uuid_date[1]) && isset($uuid_date[2])) {
                return mktime(0, 0, 0, $uuid_date[1], $uuid_date[2], $uuid_date[0]);
            }
        }
	return false;
    }

    /**
     * Lorentz crashes come in pairs which are matched up via a
     * hangid.
     *
     * @param string $hangid      of this crash report pair
     * @param string $currentUuid of this crash
     *
     * @return string uuid for the other crash in this crash pair
     */
    public function getPairedUUID($hangid, $currentUuid)
    {
        $uuidDate = date('Y-m-d', $this->uuidTimestamp($currentUuid));
        $rs = $this->db->query(
                "/* soc.web report uuid from hangid */
                    SELECT uuid
                    FROM reports
                    WHERE date_processed BETWEEN TIMESTAMP ? - CAST('1 day' AS INTERVAL) AND TIMESTAMP ? + CAST('1 day' AS INTERVAL) AND
                          hangid = ? AND uuid != ?
                    LIMIT 1
                ", array($uuidDate, $uuidDate, $hangid, $currentUuid))->current();
        if ($rs) {
            return $rs->uuid;
        } else {
            return false;
        }
    }

    /**
     * Lorentz crashes come in pairs, but if a crash is
     * resubmitted, it's possible to have more than 2
     * crash reports per hangid. This variation on
     * getPairedUUID is used via AJAX to populate
     * the UI and also to aid in debugging.
     *
     * Call retrieves all crashes related to this uuid. Does
     * not return this uuid.
     *
     * @param string $uuid of a hang crash
     *
     * @return object Database results with 'uuid'
     */
    public function getAllPairedUUIDByUUid($uuid)
    {
        $uuidDate = date('Y-m-d', $this->uuidTimestamp($uuid));
        $rs = $this->db->query(
                "/* soc.web report hangpairs from uuid */
                 SELECT uuid
                 FROM reports
                 WHERE
                     date_processed BETWEEN TIMESTAMP ? - CAST('1 day' AS INTERVAL) AND TIMESTAMP ? + CAST('1 day' AS INTERVAL) AND
                     hangid IN (
                       SELECT hangid
                       FROM reports
                       WHERE date_processed BETWEEN TIMESTAMP ? - CAST('1 day' AS INTERVAL) AND TIMESTAMP ? + CAST('1 day' AS INTERVAL) AND
                             reports.uuid = ?) AND
                     uuid != ?;", array($uuidDate, $uuidDate, $uuidDate, $uuidDate, $uuid, $uuid));
        return $rs;
    }
}
