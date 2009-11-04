<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Common model class managing the branches table.
 */
class Branch_Model extends Model {

    /**
     * Add a new record to the branches view, via the productdims and product_visibility tables.
	 * 
	 * @access 	public
	 * @param 	string 	The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
	 * @param 	string 	The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
	 * @param 	string 	The Gecko branch number (e.g. '1.9', '1.9.1', '1.9.2', '1.9.3', '1.9.4')
	 * @param 	string	The this release date for this product YYYY-MM-DD
	 * @param 	string	The this end date for this product YYYY-MM-DD (usually +90 days)
	 * @return 	object	The database query object
     */
    public function add($product, $version, $branch, $start_date, $end_date) {
		$release = $this->determine_release($version);

		$rv = $this->db->query(
			"INSERT INTO productdims (product, version, branch, release) 
			 	VALUES (?, ?, ?, ?)",
				$product, $version, $branch, $release
		);
		
		$this->db->query(
			"INSERT INTO product_visibility (productdims_id, start_date, end_date) 
				SELECT id, ? as start_date, ? as end_date 
			    FROM productdims 
			    WHERE product = ? AND version = ?
			", $start_date, $end_date, $product, $version
		);

        return $rv;
    }

    /**
     * Remove an existing record from the branches view, via the productdims tables.
	 * 
	 * @access 	public
	 * @param 	string 	The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
	 * @param 	string 	The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
	 * @return 	object	The database query object
     */
    public function delete($product, $version) {
		$rv = $this->db->query(
			"DELETE FROM productdims 
				WHERE product = ? 
				AND	version = ?
			 ", $product, $version
		);
		return $rv;
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

        $missing = $this->db->query("
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
	 * @return array 	An array of product objects
     */
    public function getProducts() {
        return $this->fetchRows(
			'/* soc.web branch.products */ 
				SELECT DISTINCT product 
				FROM branches 
				ORDER BY product
			');
    }

    /**
     * Fetch all distinct product / version combinations.
	 *
	 * @return array 	An array of version objects
     */
    public function getProductVersions() {
        return $this->fetchRows(
			'/* soc.web branch.prodversions */ 
				SELECT DISTINCT pd.id, pd.product, pd.version, pd.branch, pd.release, pv.start_date, pv.end_date
				FROM productdims pd
				INNER JOIN product_visibility pv ON pv.productdims_id = pd.id
				ORDER BY pd.product, pd.version
			');
    }

    /**
     * Fetch data on products, branches, and versions for the front 
     * page query form.
     */
    public function getBranchData() { 
        $cache_key = 'query_branch_data';
        $data = $this->cache->get($cache_key);
        if (!$data) {
            $data = array(
                'products' => $this->getProducts(),
                'branches' => $this->getBranches(),
                'versions' => $this->getProductVersions()
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
				WHERE product=? 
				AND version=?
				LIMIT 1'
				, $product, $version
			)->current();
		if (isset($result->id)) {
			return $result;
		}
		return false;
    }

    /**
     * Update the `branch` and `release` fields of an existing record in the branches view, 
 	 * via the productdims tables.
	 * 
	 * @access 	public
	 * @param 	string 	The product name (e.g. 'Camino', 'Firefox', 'Seamonkey, 'Thunderbird')
	 * @param 	string 	The version number (e.g. '3.5', '3.5.1', '3.5.1pre', '3.5.2', '3.5.2pre')
	 * @param 	string 	The Gecko branch number (e.g. '1.9', '1.9.1', '1.9.2', '1.9.3', '1.9.4')
	 * @param 	string	The this release date for this product YYYY-MM-DD
	 * @param 	string	The this end date for this product YYYY-MM-DD (usually +90 days)
	 * @return 	object	The database query object
     */
    public function update($product, $version, $branch, $start_date, $end_date) {
 		$release = $this->determine_release($version);

		$rv = $this->db->query(
			"UPDATE productdims 
				SET 
					branch = ?, 
					release = ? 
				WHERE product = ?
				AND version = ?
			 	", $branch, $release, $product, $version
		);
		
		$branch = $this->getByProductVersion($product, $version);

		$this->db->query(
			"UPDATE product_visibility
				SET start_date = ?, end_date = ?
			    WHERE productdims_id = ?
			", trim($start_date), trim($end_date), $branch->id
		);

		return $rv;
	}


	/* */
}
