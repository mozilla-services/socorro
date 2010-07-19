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
require_once(Kohana::find_file('libraries', 'versioncompare', TRUE, 'php'));

/**
 * Common model class managing the branches table.
 *
 * @package 	SocorroUI
 * @subpackage 	Models
 */
class Branch_Model extends Model {

    /**
     * Take an array of version objects, and return an array of sorted version numbers.  Return
     * array in reverse order.
     *
     * @param array An array of version objects
     * @param array An array of version numbers
     */
    private function _sortVersions($versions)
    {
        $versions_array = array();
        foreach ($versions as $version) {
            $versions_array[] = $version->version;
        }

        $vc = new VersioncompareComponent();
        $vc->sortAppversionArray($versions_array);
        rsort($versions_array);

        return $versions_array;
    }

    /**
     * Add a new record to the branches view, via the productdims and product_visibility tables.
	 * 
	 * @access 	public
	 * @param 	string 	The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
	 * @param 	string 	The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
	 * @param 	string 	The Gecko branch number (e.g. '1.9', '1.9.1', '1.9.2', '1.9.3', '1.9.4')
	 * @param 	string	The start date for this product YYYY-MM-DD
	 * @param 	string	The end date for this product YYYY-MM-DD (usually +90 days)
	 * @param   bool    True if version should be featured on the dashboard; false if not.
	 * @return 	object	The database query object
     */
    public function add($product, $version, $branch, $start_date, $end_date, $featured=false) {
		if ($product_version = $this->getByProductVersion($product, $version)) {
			return $this->update($product, $version, $branch, $start_date, $end_date, $featured);
		} else {
			$release = $this->determine_release($version);
			try {
				$rv = $this->db->query("/* soc.web branch.add */
					INSERT INTO productdims (product, version, branch, release) 
					VALUES (?, ?, ?, ?)",
					$product, $version, $branch, $release
				);
			} catch (Exception $e) {
				Kohana::log('error', "Could not add \"$product\" \"$version\" in soc.web branch.add \r\n " . $e->getMessage());
			}
			$this->addProductVisibility($product, $version, $start_date, $end_date, $featured);
			if (isset($rv)) {
				return $rv;
			}
		}
    }

    /**
     * Fetch a product from the productdims table, and add a new record to the product_visibility table.
	 * 
	 * @access 	private
	 * @param 	string 	The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
	 * @param 	string 	The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
	 * @param 	string	The release date for this product YYYY-MM-DD
	 * @param 	string	The end date for this product YYYY-MM-DD (usually +90 days)
	 * @param   bool    True if version should be featured on the dashboard; false if not.	 
	 * @return 	void
     */
	private function addProductVisibility($product, $version, $start_date, $end_date, $featured=false) {
		$this->db->query("/* soc.web branch.addProductVisibility */
				INSERT INTO product_visibility (productdims_id, start_date, end_date, featured) 
                SELECT id, ? as start_date, ? as end_date, ? as featured 
	            FROM productdims 
	            WHERE product = ? AND version = ?
		        ", $start_date, $end_date, $featured, $product, $version
		);
	}

    /**
     * Remove an existing record from the branches view, via the productdims tables.
	 * 
	 * @access 	public
	 * @param 	string 	The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
	 * @param 	string 	The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
	 * @return 	void
     */
    public function delete($product, $version) {
		if ($product_version = $this->getByProductVersion($product, $version)) {
			$this->deleteProductVisibility($product, $version);

			$rv = $this->db->query("/* soc.web branch.delete */
					DELETE FROM productdims 
					WHERE product = ? 
					AND	version = ?
			 	", $product, $version
			);
			return $rv; 
		}
	}
	
	/**
     * Remove an existing record from the branches view, via the productdims tables.
	 * 
	 * @access 	private
	 * @param 	string 	The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
	 * @param 	string 	The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
	 * @return 	void
     */
	private function deleteProductVisibility ($product, $version) {
		if ($product_version = $this->getByProductVersion($product, $version)) {
			if ($product_visibility = $this->getProductVisibility($product_version->id)) {
				$sql = "/* soc.web branch.deleteProductVisibility */
					DELETE FROM product_visibility
					WHERE productdims_id = ?
				";
				$this->db->query($sql, $product_version->id);
			}
		}
	}
	
	/**
     * Determine what the release is based on the version name given.
	 * 
	 * @access 	private
	 * @param 	string 	The version number (e.g. '3.5', '3.5.1', '3.5.1a', 3.5.1pre', '3.5.2', '3.5.2pre')
	 * @return 	string	The release string ('major', 'milestone', 'development')
     */
	private function determine_release($version)
	{
		if (strstr($version, 'pre')) {
			return 'development';
		} elseif (strstr($version, 'a') || strstr($version, 'b')) {
			return 'milestone';
		} else {
			return 'major';
		}
	}

    /**
     * Query for potential branches in reports not yet present in the branches 
     * table.
	 * 
	 * @access	public
	 * @return 	array 	An array of branches / products / versions	
     */
    public function findMissingEntries() {
		$start_date = date('Y-m-d', (time()-604800)); // 1 week ago
        $end_date = date('Y-m-d');

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
	 * @return array 	An array of branch objects
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
	 * @return 	array 	An array of branch objects
     */
    public function getBranches() { 
        return $this->fetchRows(
			'/* soc.web branch.branches */ 
				SELECT DISTINCT branch 
				FROM branches 
				ORDER BY branch
			');
    }

    /**
     * Fetch all distinct product / branch combinations.
	 * 
	 * @return array 	An array of product branches
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
	 * @return array 	An array of products
     */
    public function getProducts() {
        $results = $this->fetchRows(
			'/* soc.web branch.products */ 
				SELECT DISTINCT product 
				FROM branches 
				ORDER BY product
			');

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
 	 * @param 	int 	The id for the product/version record.
	 * @return 	array 	An array of product objects
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
	 * @return array 	An array of version objects
     */
    public function getProductVersions() {
        return $this->fetchRows(
			'/* soc.web branch.prodversions */ 
				SELECT DISTINCT pd.id, pd.product, pd.version, pd.branch, pd.release, pv.start_date, pv.end_date, pv.featured
				FROM productdims pd
				INNER JOIN product_visibility pv ON pv.productdims_id = pd.id
				ORDER BY pd.product, pd.version
			');
    }
    
    /**
     * Fetch all distinct product / version combinations that have a start date that is prior to today's
     * date and an end date that is after today's date.
     *
     * @return array    An array of version objects
     */
    public function getCurrentProductVersions() {
        $date = date("Y-m-d");
        return $this->fetchRows(
			'/* soc.web branch.prodversions */ 
				SELECT DISTINCT pd.id, pd.product, pd.version, pd.branch, pd.release, pv.start_date, pv.end_date, pv.featured
				FROM productdims pd
				INNER JOIN product_visibility pv ON pv.productdims_id = pd.id
				WHERE pv.start_date <= ?
				AND pv.end_date >= ?
				ORDER BY pd.product, pd.version
			', true, array($date, $date));
    }
    
    /**
     * Fetch all versions of a product that have a start date that is prior to today's
     * date and an end date that is after today's date.
     *
     * @param string    A product name
     * @return array    An array of version objects
     */
    public function getCurrentProductVersionsByProduct($product) {
        $date = date("Y-m-d");
        return $this->fetchRows(
			'/* soc.web branch.prodversions */ 
				SELECT DISTINCT pd.id, pd.product, pd.version, pd.branch, pd.release, pv.start_date, pv.end_date, pv.featured
				FROM productdims pd
				INNER JOIN product_visibility pv ON pv.productdims_id = pd.id
				WHERE pd.product = ?
				AND pv.start_date <= ?
				AND pv.end_date >= ?
				ORDER BY pd.product, pd.version
			', true, array($product, $date, $date));
    }

    /**
     * Fetch all of the versions for a particular product that were released between 
 	 * the specified start and end dates. Only return versions that are of a major or 
 	 * milestone release.
	 *
	 * @param 	string 	The product name
	 * @param 	string	The release date for a product YYYY-MM-DD
	 * @param 	string	The end date for this product YYYY-MM-DD (usually +90 days)
	 * @return 	array 	An array of version objects
     */
    public function getProductVersionsByDate($product, $start_date, $end_date) {
        return $this->fetchRows(
			'/* soc.web branch.prodversions */ 
				SELECT DISTINCT pd.id, pd.product, pd.version, pd.branch, pd.release, pv.start_date, pv.end_date, pv.featured
				FROM productdims pd
				INNER JOIN product_visibility pv ON pv.productdims_id = pd.id
				WHERE pd.product = ? 
				AND (pd.release = ? OR pd.release = ?)
				AND pv.start_date >= ?
				AND pv.end_date <= ?
				ORDER BY pd.product, pd.version
			', true, array($product, "major", "milestone", $start_date, $end_date));
    }

    /**
     * Fetch all of the versions for a particular product.
	 *
	 * @param 	string 	The product name
	 * @return 	array 	An array of version objects
     */
    public function getProductVersionsByProduct($product) {
        return $this->fetchRows(
			'/* soc.web branch.prodversions */ 
				SELECT DISTINCT pd.id, pd.product, pd.version, pd.branch, pd.release, pv.start_date, pv.end_date, pv.featured
				FROM productdims pd
				INNER JOIN product_visibility pv ON pv.productdims_id = pd.id
				WHERE pd.product = ? 
				ORDER BY pd.product, pd.version
			', true, array($product));
    }

	/**
	 * Fetch all distinct product / version combinations from productdims
	 * that do not have matching entries from product_visibility.
	 *
	 * @return arary 	An array of version objects
	 */
	public function getProductVersionsWithoutVisibility () {
        return $this->fetchRows('/* soc.web branch.getProductVersionsWithoutVisibility */
			SELECT DISTINCT pd.id, pd.product, pd.version, pd.branch, pd.release, pv.start_date, pv.end_date, pv.featured
			FROM productdims pd
			LEFT OUTER JOIN product_visibility pv ON pv.productdims_id = pd.id
			WHERE pv.start_date IS NULL and pv.end_date IS NULL
			ORDER BY pd.product, pd.version
		');
	}

    /**
     * Fetch data on products, branches, and versions for the front 
     * page query form.
	 * 
	 * @param 	bool	True if you want cached results; false if you don't.
	 * @param   bool    True if you want only current versions; false if you want all versions.
	 * @return 	array 	An array of products, branches and versions results.
     */
    public function getBranchData($cache=true, $current_versions=true) { 
        $cache_key = 'query_branch_data';
        if ($current_versions) {
            $cache_key = '_current';
        }
        $data = $this->cache->get($cache_key);
        
        if (!$data || !$cache) {
            $data = array(
                'products' => $this->getProducts(),
                'branches' => $this->getBranches(),
                'versions' => ($current_versions) ? $this->getCurrentProductVersions() : $this->getProductVersions()
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
        $result = $this->db->query(
				'/* soc.web branch.prodbyvers */ 
				SELECT * 
				FROM productdims 
				WHERE product = ? 
				AND version = ?
				LIMIT 1'
				, trim($product), trim($version)
			);
		if (isset($result[0]->id)) {
			return $result[0];
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
        $result = $this->db->query(
				'/* soc.web branch.prodbyvers */ 
				SELECT * 
				FROM productdims 
				WHERE product = ? 
				AND release = ?
				ORDER BY version DESC
				LIMIT 1'
				, trim($product), "major"
			);
		if (isset($result[0]->id)) {
			return $result[0];
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
        $date = date("Y-m-d");
        $versions = $this->fetchRows(
			'/* soc.web branch.getFeaturedVersions */ 
				SELECT DISTINCT pd.id, pd.product, pd.version, pd.branch, pd.release, pv.start_date, pv.end_date, pv.featured
				FROM productdims pd
				INNER JOIN product_visibility pv ON pv.productdims_id = pd.id
				WHERE pd.product = ?
				AND pv.start_date <= ?
				AND pv.end_date >= ?
				AND pv.featured = true
				ORDER BY pd.product, pd.version
			', true, array($product, $date, $date));

        if (isset($versions[0])) {
            rsort($versions);
            return $versions;
        } else {
            return $this->getFeaturedVersionsDefault($product);
        }
        return 0;
    } 

    /**
     * Determine the featured versions for a particular product if there are no 
     * versions that have been declared featured versions.
     *
     * @param string    The product name
     * @return array    An array of featured versions
     */
    private function getFeaturedVersionsDefault($product)
    {
        if ($versions = $this->getCurrentProductVersionsByProduct($product)) {
            $versions_array = $this->_sortVersions($versions);
            $featured_versions = array();
            foreach (array(Release::MAJOR, Release::MILESTONE, Release::DEVELOPMENT) as $release) {
                foreach ($versions_array as $va) {
                    foreach ($versions as $version) {
                        if (
                            !isset($featured_versions[$release]) &&
                            $version->version == $va &&
                            $version->release == $release
                        ) {
                            $featured_versions[$release] = $version;
                        }
                    }
                }
            }
            rsort($featured_versions);
            return $featured_versions;
        }
        return false;
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
               FROM product_visibility pv
               JOIN productdims pd ON pd.id = pv.productdims_id
               WHERE pd.product = ?
               AND pd.version != ?
               AND pv.featured = true
               AND pv.start_date <= ?
			   AND pv.end_date >= ?			
            '
            , trim($product), trim($version), $date, $date
        );
        if (isset($result[0]->versions_count)) {
            return $result[0]->versions_count;
        }
        return 0;
    }
    
    /**
     * Fetch all of the versions for a particular product that are not featured.
     *
     * @param string    The product name
     * @param array     An array of featured versions
     * @return array    An array of unfeatured versions
     */
    public function getUnfeaturedVersions($product, $featured_versions)
    {
        $date = date('Y-m-d');
        $versions = $this->fetchRows(
			'/* soc.web branch.getFeaturedVersions */ 
				SELECT DISTINCT pd.id, pd.product, pd.version, pd.branch, pd.release, pv.start_date, pv.end_date, pv.featured
				FROM productdims pd
				INNER JOIN product_visibility pv ON pv.productdims_id = pd.id
				WHERE pd.product = ?
				AND pv.start_date <= ?
				AND pv.end_date >= ?
				AND pv.featured = false
				ORDER BY pd.product, pd.version
			', true, array($product, $date, $date));

        if (isset($versions[0])) {
            if (isset($featured_versions) && !empty($featured_versions)) {
                foreach($featured_versions as $featured_version) {
                    foreach ($versions as $key => $version) {
                        if ($featured_version->version == $version->version) {
                            unset($versions[$key]);
                        }
                    }
                }
            }
            rsort($versions);
            return $versions;
        }
        return false;
    }

    /**
     * Update the branch and release fields of an existing record in the branches view, 
 	 * via the productdims tables.
	 * 
	 * @access 	public
	 * @param 	string 	The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
	 * @param 	string 	The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
	 * @param 	string 	The Gecko branch number (e.g. '1.9', '1.9.1', '1.9.2', '1.9.3', '1.9.4')
	 * @param 	string	The start date for this product YYYY-MM-DD
	 * @param 	string	The end date for this product YYYY-MM-DD (usually +90 days)
     * @param   bool    True if version should be featured on the dashboard; false if not. 
	 * @return 	object	The database query object
     */
    public function update($product, $version, $branch, $start_date, $end_date, $featured=false) {
		if ($product_version = $this->getByProductVersion($product, $version)) {
 			$release = $this->determine_release($version);
			$rv = $this->db->query("/* soc.web branch.update */
				UPDATE productdims 
				SET branch = ?, release = ? 
				WHERE product = ?
				AND version = ?
			 	", $branch, $release, $product, $version
			);
			$this->updateProductVisibility($product, $version, $start_date, $end_date, $featured);
			return $rv;
		} else {
			return $this->add($product, $version, $branch, $start_date, $end_date, $featured);
		}
	}

    /**
     * Update the start_date and end_date fields of an existing record in the branches view, 
 	 * via the productdims tables.
	 * 
	 * @access 	private
	 * @param 	string 	The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
	 * @param 	string 	The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
	 * @param 	string	The start date for this product YYYY-MM-DD
	 * @param 	string	The end date for this product YYYY-MM-DD (usually +90 days)
	 * @param   bool    True if version should be featured on the dashboard; false if not.	 
	 * @return 	void
     */
	private function updateProductVisibility($product, $version, $start_date, $end_date, $featured=false) {
		if ($product_version = $this->getByProductVersion($product, $version)) {
			if ($product_visibility = $this->getProductVisibility($product_version->id)) {
				$sql = "/* soc.web branch.updateProductVisibility */ 
					UPDATE product_visibility
					SET start_date = ?, end_date = ?, featured = ?
					WHERE productdims_id = ?
				"; 		
				$this->db->query($sql, trim($start_date), trim($end_date), $featured, $product_version->id);
			} else {
				$this->addProductVisibility($product, $version, $start_date, $end_date, $featured);
			}
		}
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
        $sql = "SELECT version FROM productdims WHERE product = ? AND version IN (" . join(', ', $prep) . ")";
        $bind_params = array_merge(array($product), $versions);
        return $this->fetchSingleColumn($sql, 'version', $bind_params);
    }


	/* */
}
