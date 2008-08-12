<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Common model class managing the branches table.
 */
class Branch_Model extends Model {

    /**
     * Fetch everything in the branches table
     */
    public function getAll() { 
        return $this->fetchRows('SELECT DISTINCT * FROM branches ORDER BY branch');
    }

    /**
     * Fetch the names of all unique branches
     */
    public function getBranches() { 
        return $this->fetchRows('SELECT DISTINCT branch FROM branches ORDER BY branch');
    }

    /**
     * Fetch all distinct product / branch combinations.
     */
    public function getProductBranches() {
        return $this->fetchRows('SELECT DISTINCT product, branch FROM branches ORDER BY product, branch');
    }

    /**
     * Fetch the names of all unique products.
     */
    public function getProducts() {
        return $this->fetchRows('SELECT DISTINCT product FROM branches ORDER BY product');
    }

    /**
     * Fetch all distinct product / version combinations.
     */
    public function getProductVersions() {
        return $this->fetchRows('SELECT DISTINCT product, version FROM branches ORDER BY product, version');
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

}
