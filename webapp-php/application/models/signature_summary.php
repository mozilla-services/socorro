<?php

class Signature_Summary_Model extends Model
{
    protected $_sig_cache = array();

    public function getSummary($report_type, $signature, $start, $end, $versions = array())
    {
        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $service = new Web_Service($config);
        $host = Kohana::config('webserviceclient.socorro_hostname');
        $report_type = rawurlencode($report_type);
        $signature = rawurlencode(str_replace('/', '%2F', $signature));
        $start_date = rawurlencode($start);
        $end_date = rawurlencode($end);
        $url = "{$host}/signaturesummary/report_type/{$report_type}/signature/{$signature}/start_date/{$start_date}/end_date/{$end_date}";

        if(!empty($versions)) {
            $url .= "/versions/" . rawurlencode(implode('+', $versions));
        }

        $resp = $service->get($url);

        return $resp;
    }
}
