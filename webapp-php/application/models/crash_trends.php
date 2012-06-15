<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

class Crash_Trends_Model extends Model {

    public function getCrashTrends($product, $version, $start_date, $end_date)
    {
        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $service = new Web_Service($config);
        $host = Kohana::config('webserviceclient.socorro_hostname');
        $product = rawurlencode($product);
        $version = rawurlencode($version);
        $start_date = rawurlencode($start_date);
        $end_date = rawurlencode($end_date);

        $url = "{$host}/crashtrends/start_date/{$start_date}/end_date/{$end_date}/product/{$product}/version/{$version}";

        $resp = $service->get($url);
        return $resp;
    }
}
?>
