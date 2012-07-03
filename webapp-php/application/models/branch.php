<?php defined('SYSPATH') or die('No direct script access.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

require_once(Kohana::find_file('libraries', 'release', TRUE, 'php'));

/**
 * Common model class managing the branches table.
 *
 * @package     SocorroUI
 * @subpackage  Models
 */
class Branch_Model extends Model {

    protected $cache;
    protected $admin_username;
    protected $service;

    public function __construct()
    {
        parent::__construct();
        $this->cache = Cache::instance();
        $this->admin_username = "NoAuth";
        if (Kohana::config('auth.driver') !== "NoAuth") {
            $this->admin_username = Auth::instance()->get_user();
        }

        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }

        $this->service = new Web_Service($config);

    }

    /**
     * Return a list of all product names in the products table
     * @return array And array of product names
     */
    public function getProducts()
    {
        $products = array();
        $host = Kohana::config('webserviceclient.socorro_hostname');
        $lifetime = Kohana::config('webserviceclient.topcrash_vers_rank_cache_minutes', 60) * 60;
        $response = $this->service->get($host . '/products/', 'json', $lifetime);

        foreach ($response->hits as $product) {
            array_push($products, $product->product_name);
        }
        return $products;
    }

    /**
     * Fetch get current versions via the webservice
     */
    protected function _getValues() {
        $host = Kohana::config('webserviceclient.socorro_hostname');
        $lifetime = Kohana::config('webserviceclient.branch_model_cache_in_minutes', 60) * 60;
        $resp = $this->service->get("${host}/current/versions/", 'json', $lifetime);

        return $resp->currentversions;
    }

    /**
     * Add a new record to the branches view, via the productdims and product_visibility tables.
     *
     * @access  public
     * @param   string  The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
     * @param   string  The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
     * @param   string  The release channel (e.g. 'Release', 'Beta', 'Aurora', 'Nightly')
     * @param   int     The build id
     * @param   string  The OS
     * @param   string  The repository where this release can be found
     * @param   string  The beta number (optional)
     * @return  object  The database query object
     */
    public function add($product, $version,  $release_channel, $build_id,
                        $platform, $repository, $beta_number = null)
    {
        $host = Kohana::config('webserviceclient.socorro_hostname');
        $data = array(
            'product' => $product,
            'version' => $version,
            'build_type' => $release_channel,
            'build_id' => $build_id,
            'platform' => $platform,
            'beta_number' => $beta_number,
            'repository' => $repository
        );
        $res = $this->service->post($host . '/products/builds/', $data, '');
        if ($res) {
            $this->cache->delete_all();
        }
        else {
            $res = $this->service->response_data;
        }
        return $res;
    }

    /**
     * Fetch all distinct product / version combinations.
     *
     * @return bool     True if you want to delete the previously cached data first; used by admin panel
     * @return array    An array of version objects
     */
    public function getProductVersions() {
        return $this->_getValues();
    }

    /**
     * Fetch all distinct product / version combinations that have a start date that is after today's
     * date or an end date that is before today's date.
     *
     * @param bool    True if we should delete the cached query results first
     * @return array  An array of version objects
     */
    public function getNonCurrentProductVersions($delete_cache=false) {
        $resp = $this->_getValues();

        $time = time();
        $response = array();
        foreach($resp as $item) {
            if(strtotime($item->start_date) > $time OR strtotime($item->end_date) < $time) {
                $response[] = $item;
            }
        }
        return $response;
    }

    /**
     * Fetch all distinct product / version combinations that have a start date that is prior to today's
     * date and an end date that is after today's date.
     *
     * @param  bool     True if we should delete the cached query results first; used by the admin panel
     * @return array    An array of version objects
     */
    public function getCurrentProductVersions($delete_cache=false) {
        $resp = $this->_getValues();
        $now = time();
        $result = array();
        foreach($resp as $item) {
            if(strtotime($item->start_date) <= $now AND strtotime($item->end_date) >= $now) {
                $result[] = $item;
            }
        }

        return $result;
    }

    /**
     * Fetch all versions of a product that have a start date that is prior to today's
     * date and an end date that is after today's date.
     *
     * @param string    A product name
     * @return array    An array of version objects
     */
    public function getCurrentProductVersionsByProduct($product) {
        $resp = $this->_getValues();
        $now = time();
        $result = array();
        foreach($resp as $item) {
            if(strtotime($item->start_date) <= $now AND
               strtotime($item->end_date) >= $now AND
               $item->product == $product) {
                $result[] = $item;
            }
        }

        return $result;
    }

    /**
     * Fetch all of the versions for a particular product.
     *
     * @param   string  The product name
     * @return  array   An array of version objects
     */
    public function getProductVersionsByProduct($product) {
        $resp = $this->_getValues();
        $products = array();
        foreach($resp as $item) {
            if($item->product == $product) {
                $products[] = $item;
            }
        }

        return $products;
    }

    /**
     * Fetch all distinct product / version combinations from productdims
     * that do not have matching entries from product_visibility.
     *
     * @return arary    An array of version objects
     */
    public function getProductVersionsWithoutVisibility () {
        $resp = $this->_getValues();
        foreach($resp as $k => $item) {
            if($item->start_date OR $item->end_date) {
                unset($resp[$k]);
            }
        }

        return $resp;
    }

    /**
     * Fetch data on products, branches, and versions for the front
     * page query form.
     *
     * @param   bool    True if you want cached results; false if you don't.
     * @param   bool    True if you want only current versions; false if you want all versions.
     * @param   bool    True if you want to delete the previously cached queries; used by admin panel.
     * @return  array   An array of products and versions results.
     */
    public function getBranchData($cache=true, $current_versions=true, $delete_cache=false) {
        $cache_key = 'query_branch_data';
        if ($current_versions) {
            $cache_key = '_current';
        }
        $data = $this->cache->get($cache_key);

        if (!$data || !$cache) {
            $data = array(
                'products' => $this->getProducts($delete_cache),
                'versions' => ($current_versions) ? $this->getCurrentProductVersions($delete_cache) : $this->getProductVersions($delete_cache)
            );
            $this->cache->set($cache_key, $data);
        }
        return $data;
    }

    /**
     * Fetch a single branch based on product and version.
     *
     * @param  string product
     * @param  string version
     * @return object Branch data
     */
    public function getByProductVersion($product, $version) {
        $resp = $this->_getValues();
        foreach ($resp as $item) {
            if($item->product == $product AND $item->version == $version) {
                return $item; // Essentially a LIMIT 1, per old query
            }
        }

        return false;
    }

    /**
     * Fetch the most recent major version for a product.
     *
     * @param  string product
     * @return object Branch data
     */
    public function getRecentProductVersion($product, $channel = 'Release') {
        $resp = $this->_getValues();
        $date = time();
        foreach($resp as $item) {
            if( $item->product == $product AND
                $item->release == $channel AND
                strtotime($item->start_date) <= $date AND
                strtotime($item->end_date) >= $date) {
                return $item; // Essentially a LIMIT 1, per old query
            }
        }
        return false;
    }

    /**
     * Fetch the featured versions for a particular product.
     *
     * @param string    The product name
     * @return array    An array of featured versions
     */
    public function getFeaturedVersions($product)
    {
        $resp = $this->_getValues();
        $result = array();
        $now = time();
        foreach($resp as $item) {
            if( $item->product == $product AND
                $item->featured AND
                strtotime($item->start_date) <= $now AND
                strtotime($item->end_date) >= $now) {
                $result[] = $item;
            }
        }

        return $result;
    }

    /**
     * Fetch the total number of featured versions for this product, excluding a specific version.
     *
     * @param  string product
     * @param  string version
     * @return int  Number of versions featured
     */
    public function getFeaturedVersionsExcludingVersionCount($product, $version)
    {
        $date = date('Y-m-d');
        $result = $this->db->query(
            '/* soc.web branch.getFeaturedVersionsExcludingVersionCount() */
               SELECT COUNT(*) as versions_count
               FROM product_info pd
               WHERE pd.product_name = ?
               AND pd.version_string != ?
               AND pd.is_featured = true
               AND pd.start_date <= ?
               AND pd.end_date >= ?
            '
            , trim($product), trim($version), $date, $date
        );
        if (isset($result[0]->versions_count)) {
            return $result[0]->versions_count;
        }
        return 0;

        $resp = $this->_getValues();
        $result = 0;
        $date = time();
        foreach($resp as $item) {
            if( $item->product == $product AND
                $item->version != $version AND
                $item->featured AND
                strtotime($item->start_date) <= $date AND
                strtotime($item->end_date) >= $date) {
                $result++;
            }
        }

        return $result;

    }

    /**
     * Fetch all of the versions for a particular product that are not featured.
     *
     * @param string    The product name
     * @return array    An array of unfeatured versions
     */
    public function getUnfeaturedVersions($product)
    {
        $resp = $this->_getValues();
        $result = array();
        $now = time();
        foreach($resp as $item) {
            if( $item->product == $product AND
                ! $item->featured AND
                strtotime($item->start_date) <= $now AND
                strtotime($item->end_date) >= $now) {
                $result[] = $item;
            }
        }

        return $result;
    }

    /**
     * Given a list of versions for a product, returns only the
     * versions which are in the system.
     *
     * @param string $product  - Name of a product
     * @param array  $versions - List of version numbers (string)
     *
     * @return array of strings
     */
    public function verifyVersions($product, $versions)
    {
        $versions_list = array();
        foreach ($versions as $version) {
            $versions_list[] = rawurlencode($product . ':' . $version);
        }
        $versions_string = implode('+', $versions_list);

        $host = Kohana::config('webserviceclient.socorro_hostname');
        $lifetime = Kohana::config('webserviceclient.topcrash_vers_rank_cache_minutes', 60) * 60;
        $response = $this->service->get($host . '/products/versions/' . $versions_string . '/',
                                        'json', $lifetime);

        $results = array();
        foreach ($response->hits as $version) {
            array_push($results, $version->version);
        }
        return $results;
    }

    /**
     * Update the list of featured versions for each given product.
     *
     * @param array $featured Associative array of product name and versions list.
     * @return Result from the middleware service.
     */
    public function update_featured_versions($featured)
    {
        $data = array();
        foreach ($featured as $product => $versions) {
            $data[$product] = $versions;
        }

        $host = Kohana::config('webserviceclient.socorro_hostname');
        $response = $this->service->put($host . '/releases/featured/', $data);

        $json_response;
        if ($response === TRUE) {
            // If the featured version was successfully updated, clear all caches
            $this->cache->delete_all();

            $json_response->{'status'} = 'success';
            $json_response->{'message'} = 'Featured version(s) was successfully updated.';
        } else {
            $json_response->{'status'} = 'failed';
            $json_response->{'message'} = 'Error: ' . $response;
        }
        return $json_response;
    }
}
