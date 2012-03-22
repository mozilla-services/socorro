<?php

class Signature_Summary_Model extends Model {

    protected $_sig_cache = array();

    public function getSummary($report_type, $signature, $start, $end, $versions = array())
    {

        if(!empty($versions)) {
            $versions = $this->_calculateVersionIds($versions);
        }

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

        if(isset($versions['products']) && !empty($versions['products'])) {
            $url .= "/product/{$versions['products']}";
        }

                if(isset($versions['versions']) && !empty($versions['versions'])) {
                                $url .= "/versions/{$versions['versions']}";
                                        }

        $resp = $service->get($url);

        return $resp;
    }

    protected function _calculateVersionIds(array $versions)
    {
        $versions_new = array();
        $products_new = array();

        foreach($versions as $version) {
            $vs = explode(':', $version);
            if(count($vs) != 2) {
                $products_new[] = $version; // Just in case we get a single product.
                continue;
            }
            $product = $vs[0];
            $version = $this->db->escape($vs[1]);
            if (isset($this->_sig_cache[$product . $version])) {
                $versions_new[] = $this->_sig_cache[$product . $version];
                $products_new[] = $product;
            } else {
                $sql = "SELECT product_version_id FROM product_versions WHERE product_name = ";
                $sql .= $this->db->escape($product);
                $sql .= " AND version_string = {$version}";

                $version_id = $this->db->query($sql)->as_array();
                $version_id = $version_id[0]->product_version_id;
                $this->_sig_cache[$product . $version] = $version_id;
                $versions_new[] = $version_id;
                if(!in_array($product, $products_new)) {
                    $products_new[] = $product;
                }
            }
        }
        $results = array();
        $results['products'] = implode('+', $products_new);
        $results['versions'] = implode('+', $versions_new);
        return $results;
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
