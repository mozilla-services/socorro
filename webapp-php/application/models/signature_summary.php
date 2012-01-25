<?php

class Signature_Summary_Model extends Model {

    protected $_sig_cache = array();

    public function getSummary($report_type, $signature, $start, $end, $product = 'Firefox', $versions = array())
    {
        if(!empty($versions)) {
            $versions = $this->_calculateVersionIds($product, $versions);
        }

        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $service = new Web_Service($config);
        $host = Kohana::config('webserviceclient.socorro_hostname');
        $report_type = rawurlencode($report_type);
        $signature = rawurlencode($signature);
        $product = rawurlencode($product);
        $url = "{$host}/signaturesummary/report_type/{$report_type}/signature/{$signature}/start_date/{$start}/end_date/{$end}/product/{$product}";

        if($versions) {
            $url .= "/versions/{$versions}";
        }
        $resp = $service->get($url);
        return $resp;
    }

    protected function _calculateVersionIds($product, array $versions)
    {
        $versions_new = array();
        $product = $this->db->escape($product);
        foreach($versions as $version) {
            $version = $this->db->escape($version);
            if (isset($this->_sig_cache[$version])) {
                $versions_new[] = $this->_sig_cache[$version];
            } else {
                $sql = "SELECT product_version_id FROM product_versions WHERE product_name = {$product} AND version_string = {$version}";

                $version_id = $this->db->query($sql)->as_array();
                $version_id = $version_id[0]->product_version_id;
                $this->_sig_cache[$version] = $version_id;
                $versions_new[] = $version_id;
            }
        }
        return implode('+', $versions_new);
    }

    public function search_signature_table($signature_string)
    {
        if(isset($this->sig_cache[$signature_string])) {
            return $this->sig_cache[$signature_string];
        }

        $ss_c = $this->db->escape($signature_string);
        $sql = "SELECT signature_id FROM signatures WHERE signature = $ss_c";
        $result = $this->db->query($sql)->as_array();
        if($result) {
            $val = $result[0]->signature_id;
            $this->sig_cache[$signature_string] = $val;
            return $val;
        } else {
            return FALSE;
        }
    }
}
