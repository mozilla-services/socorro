/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
       $end_date = rawurlencode(date('Y-m-d', TimeUtil::roundOffByMinutes($cache_in_minutes)));
       $limit = rawurlencode(Kohana::config('hang_report.byversion_limit', 300));
       $p = rawurlencode($product);
       $v = rawurlencode($version);
       $pg = rawurlencode($page);
       $dur = rawurlencode($duration);

       $resp = $service->get("${host}/reports/hang/p/${p}/v/${v}/end/${end_date}/duration/${dur}/listsize/${limit}/page/${pg}");
       if($resp) {
           return $resp;
        }
        return false;
    }
}
