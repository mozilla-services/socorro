<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Common model class managing the branches table.
 */
class Branch_Model extends Model {

    /**
     * Fetch everything in the branches table
     */
    public function getAll() { 
      return $this->fetchRows('/* soc.web branch.all */ SELECT DISTINCT * FROM branches ORDER BY branch');
    }

    /**
     * Fetch the names of all unique branches
     */
    public function getBranches() { 
        return $this->fetchRows('/* soc.web branch.branches */ SELECT DISTINCT branch FROM branches ORDER BY branch');
    }

    /**
     * Fetch all distinct product / branch combinations.
     */
    public function getProductBranches() {
        return $this->fetchRows('/* soc.web branch.prodbranches */ SELECT DISTINCT product, branch FROM branches ORDER BY product, branch');
    }

    /**
     * Fetch the names of all unique products.
     */
    public function getProducts() {
        return $this->fetchRows('/* soc.web branch.products */ SELECT DISTINCT product FROM branches ORDER BY product');
    }

    /**
     * Fetch all distinct product / version combinations.
     */
    public function getProductVersions() {
        return $this->fetchRows('/* soc.web branch.prodversions */ SELECT DISTINCT product, version FROM branches ORDER BY product, version');
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

        $branch = $this->db->query( '/* soc.web branch.prodbyvers */ SELECT branches.* FROM branches WHERE branches.product=? AND branches.version=?', $product, $version)->current();
        if (!$branch) return FALSE;

        return $branch;
    }

}
