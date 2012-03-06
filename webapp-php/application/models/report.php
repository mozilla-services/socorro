<?php defined('SYSPATH') or die('No direct script access.');

/**
 * Common model class managing the branches table.
 */
class Report_Model extends Model {

    /**
     * The Web Service class.
     */
    protected $service = null;

    public function __construct()
    {
        parent::__construct();

        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }

        $this->service = new Web_Service($config);
    }

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
        $raw_json = $this->getRawJson($uuid);

        if ($crash_report_json === false) {
            Kohana::log('info', "$uuid could not fetch processed JSON");
            return false;
        } else if ($crash_report_json === true) {
            Kohana::log('info', "$uuid was reported but not processed; a priority job has been scheduled.");
            return true;
        } else if ( !is_bool($crash_report_json) ) {
            $uri = Kohana::config('webserviceclient.socorro_hostname') . '/crash/uuid/' . rawurlencode($uuid);
            $report = $this->service->get($uri);
            if (!$report || $report->total == 0) {
                Kohana::log('info', "$uuid processed crash exists in HBase but does not exist in the reports table");
                return false;
            }

            $report = $report->hits[0]; // Use only crash data sent back from the service

            $crashReportDump->populate($report, $crash_report_json, $raw_json);
            return $report;
        } else {
            Kohana::log('info', "$uuid doesn't exist (404)");
            return NULL;
        }
    }

    public function getRawJson($uuid){
        $uri = Kohana::config('webserviceclient.socorro_hostname').'/crash/meta/by/uuid/'.rawurlencode($uuid);
        $result = $this->service->get($uri);
        return $result;
    }



    /**
     * Determine whether or not the raw dumps are still on the system and return the URLs
     * by which they may be downloaded.  UUID must contain a timestamp that is within the given
     * acceptable timeframe found in Kohana::config('application.raw_dump_availability').
     *
     * @param   string  The $uuid for the dump
     * @return  array|bool  Return an array containing the dump and json urls for download; else
     *                  return false if unavailable
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
     * Determine the timestamp for this report by the given UUID.
     *
     * @access  public
     * @param   string  The $uuid for this report
     * @return  int     The timestamp for this report.
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

    /**
     * Find all crash reports for the given search parameters and
     * paginate the results.
     *
     * @param params array Parameters that vary
     * @param result_number integer Number of results to return
     * @param result_offset integer First page of results to return
     * @return object containing a total count and an array of objects
     */
    public function crashesList($params, $result_number, $result_offset)
    {
        $params['result_number'] = $result_number;
        $params['result_offset'] = $result_offset;

        $uri = $this->buildURI($params, 'report/list');
        $res = $this->service->get($uri);
        //~ echo '<pre>',var_dump($uri),'</pre>';
        return $res;
    }

   /**
     * Fetch all of the comments associated with a particular Crash Signature.
     *
     * @access  public
     * @param   string A Crash Signature
     * @return  array   An array of comments
     * @see getCommentsBySignature
     */
    public function getCommentsBySignature($signature) {
        $params = array('signature' => $signature);
        return $this->getCommentsByParams($params);
    }

    /**
     * Fetch all of the comments associated with a particular Crash Signature.
     *
     * @access  public
     * @param   array   An array of parameters
     * @return  array   An array of comments
     */
    public function getCommentsByParams($params) {
        $uri = $this->buildURI($params, 'crashes/comments');
        $res = $this->service->get($uri);
        //~ echo '<pre>',var_dump($uri),'</pre>';

        if (!$res) {
            return null;
        }

        return $res->hits;
    }

    private function buildURI($params, $apiEntry)
    {
        $separator = '/';
        $apiData = array(
            Kohana::config('webserviceclient.socorro_hostname'),
            $apiEntry,
            'signature',
            rawurlencode(str_replace('/', '%2F', $params['signature']))
        );

        //echo '<pre>',var_dump($params),'</pre>';

        foreach ($params as $key => $value)
        {
            if (!empty($value))
            {
                // Be sure to add the value only if we know the param and we added a key for it
                $unknownParam = false;

                switch ($key)
                {
                    case 'query_search':
                        $apiData[] = 'fields';
                        break;
                    case 'product':
                        $apiData[] = 'products';
                        $value = implode('+', $value);
                        break;
                    case 'version':
                        $apiData[] = 'versions';
                        $value = implode('+', $value);
                        break;
                    case 'query_type':
                        $apiData[] = 'search_mode';
                        switch ($value)
                        {
                            case 'startswith':
                                $value = 'starts_with';
                                break;
                            case 'exact':
                                $value = 'is_exactly';
                                break;
                        }
                        break;
                    case 'date':
                        $apiData[] = 'to';
                        $value = date( 'Y-m-d H:i:s', strtotime($value) );
                        break;
                    case 'range_value':
                        if (!empty($params['range_unit']))
                        {
                            $apiData[] = 'from';

                            // Building the from_date given a number of weeks, days or hours.
                            $fromDate = !empty($params['date']) ? strtotime($params['date']) : time();
                            switch ($params['range_unit'])
                            {
                                case 'hours':
                                    $diff = strtotime( '-'.$value.' hours', $fromDate );
                                    break;
                                case 'days':
                                    $diff = strtotime( '-'.$value.' days', $fromDate );
                                    break;
                                case 'weeks':
                                default:
                                    $diff = strtotime( '-'.$value.' weeks', $fromDate );
                                    break;
                            }
                            $value = date('Y-m-d H:i:s', $diff);
                        }
                        break;
                    case 'platform':
                        $apiData[] = 'os';
                        $value = implode('+', $value);
                        break;
                    case 'reason':
                        $apiData[] = 'reasons';
                        break;
                    case 'branch':
                        $apiData[] = 'branches';
                        $value = implode('+', $value);
                        break;
                    case 'build_id':
                        $apiData[] = 'build_ids';
                        break;
                    case 'hang_type':
                        $apiData[] = 'report_type';
                        break;
                    case 'process_type':
                        $apiData[] = 'report_process';
                        break;
                    case 'plugin_field':
                        $apiData[] = 'plugin_in';
                        break;
                    case 'plugin_query_type':
                        $apiData[] = 'plugin_search_mode';
                        switch ($value)
                        {
                            case 'startswith':
                                $value = 'starts_with';
                                break;
                            case 'exact':
                                $value = 'is_exactly';
                                break;
                        }
                        break;
                    case 'plugin_query':
                        $apiData[] = 'plugin_terms';
                        break;
                    case 'result_offset':
                        $apiData[] = 'result_offset';
                        break;
                    case 'result_number':
                        $apiData[] = 'result_number';
                        break;
                    case 'force_api_impl':
                        $apiData[] = 'force_api_impl';
                        break;
                    default:
                        $unknownParam = true;
                }

                if (!$unknownParam)
                {
                    // Securing encoded "/" because of Apache refusing them in URIs
                    $value = str_replace('/', '%2F', $value);
                    $apiData[] = rawurlencode($value);
                }
            }
        }

        $apiData[] = '';    // Trick to have the closing '/'

        return implode($separator, $apiData);
    }
}
