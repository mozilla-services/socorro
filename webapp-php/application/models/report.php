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
 
require_once(Kohana::find_file('libraries', 'crash', TRUE, 'php'));

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
                SELECT reports.email, reports.url
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
        $crash = new Crash;
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
        $crash = new Crash;
        $uuidDate = date('Y-m-d', $crash->parseOOIDTimestamp($uuid));
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
