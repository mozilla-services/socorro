<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Provide data access to web services. Analogous to Kohana's Database class.
 *
 * @category Libraries
 * @package  WebServices
 * @author   Austin King <ozten@mozilla.com>
 */
class Web_Service
{
    /**
     * Config params for use with CURL
     */
    protected $config;

    /**
     * The HTTP Status code from the cURL request.
     */
    public $status_code = 0;

    /**
     * Creates an instance of this class and allows overriding default config
     *
     * @param array $config Config options
     *
     * @see config/webserviceclient.php for supported options
     */
    public function __construct($config=array())
    {
        $defaults = Kohana::config('webserviceclient.defaults');
        $this->config = array_merge($defaults, $config);

        $required_config_params = array('connection_timeout', 'timeout');
        foreach ($required_config_params as $param) {
            if (! array_key_exists($param, $this->config)) {
                trigger_error("Bad Config for a Web_Service instance, missing required parameter [$param]", E_USER_ERROR);
            }
        }
    }

    /**
     * Makes a GET request for the resource and parses the response based
     * on the expected type. By default caching is disabled
     *
     * @param string  $url             the url for the web service including any paramters
     * @param string  $response_type    the expected response type - xml, json, etc
     * @param integer $cache_lifetime the lifetime (in seconds) of a cache item or 'default'
     *     to use app wide cache default, or lastly NULL to disable caching
     *
     * @return object - the response or FALSE if there was an error
     */
    public function get($url, $response_type='json', $cache_lifetime=null)
    {
        Kohana::log('debug', 'Trying to get URL: ' . $url);

        if (is_null($cache_lifetime)) {
            $this->status_code = 200;
            return $this->_get($url, $response_type);
        }

        $cache = new Cache();
        $cache_key = 'webservice_' . md5($url . $response_type);
        $data = $cache->get($cache_key);
        if ($data) {
            StatsD::increment("webservice.cache.hits");
            return $data;
        }

        StatsD::increment("webservice.cache.misses");
        $data = $this->_get($url, $response_type);
        if ($data) {
            if ($cache_lifetime == 'default') {
                $cache->set($cache_key, $data);
            } else {
                $cache->set($cache_key, $data, null, $cache_lifetime);
            }
        }
        return $data;
    }

    /**
     * Makes a POST request for the resource and parses the response based
     * on the expected type.
     *
     * @param string $url           The url for the web service including any paramters
     * @param array  $data          An associative array of form key values
     * @param string $response_type The expected response type - xml, json, etc
     *
     * @return object - the response or FALSE if there was an error
     */
    public function post($url, $data, $response_type='json')
    {
        Kohana::log('debug', 'Trying to post to URL: ' . $url . ' with data: ' . var_export($data, true));

        $curl = $this->_initCurl($url);
        curl_setopt($curl, CURLOPT_POST, true);
        curl_setopt($curl, CURLOPT_POSTFIELDS, $data);
        $before = microtime(true);
        $curl_response = curl_exec($curl);
        $after = microtime(true);
        $t = $after - $before;
        if ($t > 3) {
            Kohana::log('alert', "Web_Service " . $t . " seconds to access $url");
        }

        $headers  = curl_getinfo($curl);
        $status_code = $headers['http_code'];
        $code = curl_errno($curl);
        $message = curl_error($curl);
        curl_close($curl);

        StatsD::increment("webservice.responses.post.".$status_code);

        if ($status_code == 200 || $status_code == 202) {
            if ($response_type == 'json') {
                $data = json_decode($curl_response);
            } else {
                $data = $curl_response;
            }
            return $data;
        }

        // See http://curl.haxx.se/libcurl/c/libcurl-errors.html
        Kohana::log('error', "Web_Service $code $message while retrieving $url which was HTTP status $this->status_code");
        return false;
    }

    /**
     * Makes a PUT request for the resource and parses the response based
     * on the expected type.
     *
     * @param string $url           The url for the web service including any paramters
     * @param array  $data          An associative array of form key values
     * @param string $response_type The expected response type - xml, json, etc
     *
     * @return object - the response or FALSE if there was an error
     */
    public function put($url, $data, $response_type='json')
    {
        Kohana::log('debug', 'Trying to put to URL: ' . $url . ' with data: ' . var_export($data, true));

        $curl = $this->_initCurl($url);
        curl_setopt($curl, CURLOPT_CUSTOMREQUEST, 'PUT');
        curl_setopt($curl, CURLOPT_POSTFIELDS, $data);
        $before = microtime(true);
        $curl_response = curl_exec($curl);
        $after = microtime(true);
        $t = $after - $before;
        if ($t > 3) {
            Kohana::log('alert', "Web_Service " . $t . " seconds to access $url");
        }

        $headers  = curl_getinfo($curl);
        $status_code = $headers['http_code'];
        $code = curl_errno($curl);
        $message = curl_error($curl);
        curl_close($curl);

        StatsD::increment("webservice.responses.put.".$status_code);

        if ($status_code == 200 || $status_code == 202) {
            if ($response_type == 'json') {
                $data = json_decode($curl_response);
            } else {
                $data = $curl_response;
            }
            return $data;
        }

        // See http://curl.haxx.se/libcurl/c/libcurl-errors.html
        Kohana::log('error', "Web_Service $code $message while retrieving $url which was HTTP status $this->status_code");
        return false;
    }

    /**
     * Makes a GET request for the resource and parses the response based
     * on the expected type
     *
     * @param string - the url for the web service including any paramters
     * @param string - the expected response type - xml, json, etc
     * @return object - the response or FALSE if there was an error
     */
    private function _get($url, $response_type)
    {
        $curl = $this->_initCurl($url);
        $before = microtime(TRUE);
        $curl_response = curl_exec($curl);
        $after = microtime(TRUE);
        $t = $after - $before;
        if ($t > 3) {
            Kohana::log('alert', "Web_Service " . $t . " seconds to access $url");
        }
        $headers  = curl_getinfo($curl);
        $this->status_code = $headers['http_code'];
        $code = curl_errno($curl);
        $message = curl_error($curl);
        curl_close($curl);

        StatsD::increment("webservice.responses.get.".$this->status_code);

        if ($this->status_code == 200 || $this->status_code == 202) {
            if ($response_type == 'json') {
                $data = json_decode($curl_response);
            } else {
                $data = $curl_response;
            }
            return $data;
        }

        // See http://curl.haxx.se/libcurl/c/libcurl-errors.html
        Kohana::log('error', "Web_Service $code $message while retrieving $url which was HTTP status $this->status_code");
        return FALSE;
    }

    /**
     * Prepares CURL for web serivce calls
     * @param string - the url for the web service including any paramters
     * @return object - handle to the curl instance
     */
    private function _initCurl($url)
    {
        $curl = curl_init($url);
        curl_setopt($curl, CURLOPT_CONNECTTIMEOUT, $this->config['connection_timeout']);
        curl_setopt($curl, CURLOPT_TIMEOUT, $this->config['timeout']);
        curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($curl, CURLOPT_ENCODING , "x-gzip");
        if (array_key_exists('basic_auth', $this->config) &&
            is_array($this->config['basic_auth'])) {
                $user = $this->config['basic_auth']['username'];
                $pass = $this->config['basic_auth']['password'];
                curl_setopt($curl, CURLOPT_USERPWD, $user . ":" . $pass);
                Kohana::log('info', "Using $user and a password for basic auth");
        }
        return $curl;
    }

}
?>
