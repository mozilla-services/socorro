<?php
/**
 * Manage data from the hang/crash pair report.
 */
class HangReport_Model extends Model {

    /**
     * Fetch the hang/crash pair data via a web service call.
     *
     * @param   string      The product name
     * @param   string      The version number
     * @param   int         The number of days
     * @return  array       Returns
     */
    public function getHangReportViaWebService($product, $version, $duration, $page)
    {
        $config = array();
       $credentials = Kohana::config('webserviceclient.basic_auth');
       if ($credentials) {
           $config['basic_auth'] = $credentials;
       }
       $service = new Web_Service($config);
       $host = Kohana::config('webserviceclient.socorro_hostname');
       $cache_in_minutes = Kohana::config('webserviceclient.hang_report_cache_minutes', 60);
       $end_date = date('Y-m-d', TimeUtil::roundOffByMinutes($cache_in_minutes));
       $limit = Kohana::config('hang_report.byversion_limit', 300);
       $p = urlencode($product);
       $v = urlencode($version);
       $pg = urlencode($page);

       $resp = $service->get("${host}/reports/hang/p/${p}/v/${v}/end/${end_date}/duration/${duration}/listsize/${limit}/page/${pg}");
       if($resp) {
           return $resp;
        }
        return false;
    }
}
