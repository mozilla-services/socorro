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
 * Contributor(s):
 *   Ryan Snyder <rsnyder@mozilla.com>
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

require_once(Kohana::find_file('libraries', 'release', TRUE, 'php'));

/**
 * Common model class managing the branches table.
 *
 * @package     SocorroUI
 * @subpackage  Models
 */
class Branch_Model extends Model {

    protected $cache;

    public function __construct()
    {
        parent::__construct();
        $this->cache = Cache::instance();
    }

    /**
     * Fetch get current versions via the webservice
     */
    protected function _getValues() {
        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $service = new Web_Service($config);
        $host = Kohana::config('webserviceclient.socorro_hostname');
        $lifetime = Kohana::config('webserviceclient.branch_model_cache_in_minutes', 60) * 60;
        $resp = $service->get("${host}/current/versions/", 'json', $lifetime);

        return $resp->currentversions;
    }

    /**
     * Add a new record to the branches view, via the productdims and product_visibility tables.
     *
     * @access  public
     * @param   string  The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
     * @param   string  The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
     * @param   string  The Gecko branch number (e.g. '1.9', '1.9.1', '1.9.2', '1.9.3', '1.9.4')
     * @param   string  The start date for this product YYYY-MM-DD
     * @param   string  The end date for this product YYYY-MM-DD (usually +90 days)
     * @param   bool    True if version should be featured on the dashboard; false if not.
     * @param   float   The throttle value for this version.
     * @return  object  The database query object
     */
    public function add($product, $version,  $start_date, $end_date, $featured=false, $throttle) {
        if ($product_version = $this->getByProductVersion($product, $version)) {
            return $this->update($product, $version, $start_date, $end_date, $featured, $throttle);
        }

        $release = $this->determine_release($version);
        try {
            $rv = $this->db->query("/* soc.web branch.add */
                SELECT * FROM edit_product_info(null, ?, ?, ?, ?, ?, ?, ?)",
                $product, $version, $release, $start_date, $end_date,
                $featured, $throttle);
        } catch (Exception $e) {
            Kohana::log('error', "Could not add \"$product\" \"$version\" in soc.web branch.add \r\n " . $e->getMessage());
        }
        $this->cache->delete_all();
        return $rv;
    }

    /**
     * Remove an existing record from the branches view, via the productdims tables.
     *
     * @access  public
     * @param   string  The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
     * @param   string  The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
     * @return  void
     */
    public function delete($product, $version) {
        if ($product_version = $this->getByProductVersion($product, $version)) {
            if ($product_visibility = $this->getProductVisibility($product_version->id)) {
                $sql = "/* soc.web branch.deleteProductVisibility */
                    DELETE FROM product_visibility
                    WHERE productdims_id = ?
                ";
                $this->db->query($sql, $product_version->id);
            }

            $rv = $this->db->query("/* soc.web branch.delete */
                    DELETE FROM productdims
                    WHERE product = ?
                    AND version = ?
                ", $product, $version
            );
            $this->cache->delete_all();
            return $rv;
        }
    }

    /**
     * Determine what the release is based on the version name given.
     *
     * @access  private
     * @param   string  The version number (e.g. '3.5', '3.5.1', '3.5.1a', 3.5.1pre', '3.5.2', '3.5.2pre')
     * @return  string  The release string ('major', 'milestone', 'development')
     */
    private function determine_release($version)
    {
        if (strstr($version, 'pre')) {
            return 'development';
        }
        if (strstr($version, 'a') || strstr($version, 'b')) {
            return 'milestone';
        }
        return 'major';
    }

    /**
     * Query for potential branches in reports not yet present in the branches
     * table.
     *
     * @access  public
     * @return  array   An array of branches / products / versions
     */
    public function findMissingEntries() {
        $start_date = date('Y-m-d', (time()-604800)); // 1 week ago
        $end_date = date('Y-m-d', time() + 86400); // Make sure we get ALL of today

        $missing = $this->db->query("/* soc.web branch.findMissingEntries */
            SELECT
                reports.product,
                reports.version,
                COUNT(reports.product) AS total
            FROM
                reports
            LEFT OUTER JOIN
                branches ON
                    reports.product = branches.product AND
                    reports.version = branches.version
            WHERE
                branches.branch IS NULL AND
                reports.product IS NOT NULL AND
                reports.version IS NOT NULL AND
                reports.date_processed >= timestamp without time zone '".$start_date."' AND
                reports.date_processed < timestamp without time zone '".$end_date."'
            GROUP BY
                reports.product, reports.version
        ");

        return $missing;
    }

    /**
     * Fetch everything in the branches table
     *
     * @return array    An array of branch objects
     */
    public function getAll() {
      return $this->fetchRows(
        '/* soc.web branch.all */
            SELECT DISTINCT *
            FROM branches
            ORDER BY branch
        ');
    }

    /**
     * Fetch the names of all unique branches
     *
     * @param  bool     True if we should remove the cached query results, used in admin panel
     * @return  array   An array of branch objects
     */
    public function getBranches($delete_cache=false) {
        $sql = '/* soc.web branch.branches */
            SELECT DISTINCT branch
            FROM branches
            ORDER BY branch
        ';

        if ($delete_cache) {
            $this->cache->delete($this->queryHashKey($sql));
        }

        return $this->fetchRows($sql);
    }

    /**
     * Fetch all distinct product / branch combinations.
     *
     * @return array    An array of product branches
     */
    public function getProductBranches() {
        return $this->fetchRows(
            '/* soc.web branch.prodbranches */
                SELECT DISTINCT product, branch
                FROM branches
                ORDER BY product, branch
            ');
    }

    /**
     * Fetch the names of all unique products.
     *
     * @param  bool     True if we should remove the cached query results, used in admin panel
     * @return array    An array of products
     */
    public function getProducts($delete_cache=false) {
        $sql = '/* soc.web branch.products */
            SELECT DISTINCT product
            FROM branches
            ORDER BY product
        ';

        if ($delete_cache) {
            $this->cache->delete($this->queryHashKey($sql));
        }

        $results = $this->fetchRows($sql);
        if (isset($results[0])) {
            $products = array();
            foreach ($results as $result) {
                array_push($products, $result->product);
            }
            return $products;
        }
        return false;
    }

    /**
     * Fetch a record from the product_visibility table by its productdims_id.
     *
     * @param   int     The id for the product/version record.
     * @return  array   An array of product objects
     */
    public function getProductVisibility($productdims_id) {
        $sql = "
            /* soc.web branch.getProductVisibility */
            SELECT *
            FROM product_visibility
            WHERE productdims_id = ?
        ";
        return $this->fetchRows($sql, true, array($productdims_id));
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
     * Fetch all of the versions for a particular product that were released between
     * the specified start and end dates. Only return versions that are of a major or
     * milestone release.
     *
     * @param   string  The product name
     * @param   string  The release date for a product YYYY-MM-DD
     * @param   string  The end date for this product YYYY-MM-DD (usually +90 days)
     * @return  array   An array of version objects
     */
    public function getProductVersionsByDate($product, $start_date, $end_date) {
        $resp = $this->_getValues();
        $start_date = strtotime($start_date);
        $end_date = strtotime($end_date);
        $result = array();
        foreach($resp as $item) {
            if( strtotime($item->start_date) >= $start_date AND
                strtotime($item->end_date) <= $end_date AND
                $item->product == $product AND
                ($item->release == 'Release' OR $item->release == 'Beta')) {
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
     * @return  array   An array of products, branches and versions results.
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
                'branches' => $this->getBranches($delete_cache),
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
    public function getRecentProductVersion($product) {
        $resp = $this->_getValues();
        $date = time();

        foreach($resp as $item) {
            if( $item->product == $product AND
                $item->release == 'Release' AND
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
     */
    public function getUnfeaturedVersions($product)
    {
        $date = date('Y-m-d');
        $sql = '/* soc.web branch.getFeaturedVersions */
                SELECT product_name as product,
                    version_string as version, is_featured as featured,
                    build_type as release, start_date, end_date, throttle
                FROM product_info
                WHERE product_name = ' . $this->db->escape($product) . '
                AND start_date <= ' . $this->db->escape($date) . '
                AND end_date >= ' . $this->db->escape($date) . '
                AND is_featured = false
                ORDER BY product_version_id, version_sort';

        return $this->fetchRows($sql);
    }

    /**
     * Update the branch and release fields of an existing record in the branches view,
     * via the productdims tables.
     *
     * @access  public
     * @param   string  The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
     * @param   string  The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
     * @param   string  The Gecko branch number (e.g. '1.9', '1.9.1', '1.9.2', '1.9.3', '1.9.4')
     * @param   string  The start date for this product YYYY-MM-DD
     * @param   string  The end date for this product YYYY-MM-DD (usually +90 days)
     * @param   bool    True if version should be featured on the dashboard; false if not.
     * @param   float   The throttle value for this version
     * @return  object  The database query object
     */
    public function update($product, $version,  $start_date, $end_date, $featured=false, $throttle) {
        $product_version = $this->getByProductVersion($product, $version);
        $prod_id = $product_version->id;
        $channel = $product_version->release;
        $release = $this->determine_release($version);
        $rv = $this->db->query("/* soc.web branch.update */
            SELECT * FROM edit_product_info(?, ?, ?, ?, ?, ?, ?, ?)", $prod_id, $product,  $version, $channel, $start_date, $end_date, $featured, $throttle);

        $this->cache->delete_all();
        return $rv;
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
        $prep = array();
        foreach ($versions as $version) {
            array_push($prep, '?');
        }
        $sql = "SELECT version_string as version FROM product_info
                WHERE product_name = ?
                AND version_string IN (" . join(', ', $prep) . ")";
        $bind_params = array_merge(array($product), $versions);
        return $this->fetchSingleColumn($sql, 'version', $bind_params);
    }
}
