<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Reporting on top crasher causes
 */
class Topcrasher_Controller extends Controller {

    public function __construct()
    {
        parent::__construct();
        $this->topcrashers_model = new Topcrashers_Model();
    }

    public function index() {
        $branch_data = $this->branch_model->getBranchData();
        $platforms   = $this->platform_model->getAll();

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));

        $this->setViewData(array(
            'all_products'  => $branch_data['products'],
            'all_branches'  => $branch_data['branches'],
            'all_versions'  => $branch_data['versions'],
            'all_platforms' => $platforms
        ));

    }

    public function byversion($product, $version, $build_id=NULL) {
        list($last_updated, $top_crashers) = 
            $this->topcrashers_model->getTopCrashers($product, $version, $build_id);

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));

        $this->setViewData(array(
            'product'      => $product,
            'version'      => $version,
            'build_id'     => $build_id,
            'last_updated' => $last_updated,
            'top_crashers' => $top_crashers
        ));
    }

    public function bybranch($branch) {

        list($last_updated, $top_crashers) = 
            $this->topcrashers_model->getTopCrashers(NULL, NULL, NULL, $branch);

        cachecontrol::set(array(
            'expires' => time() + (60 * 60)
        ));

        $this->setViewData(array(
            'branch'       => $branch,
            'last_updated' => $last_updated,
            'top_crashers' => $top_crashers
        ));

    }

}
