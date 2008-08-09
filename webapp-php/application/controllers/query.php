<?php defined('SYSPATH') or die('No direct script access.');
/**
 *
 */
class Query_Controller extends Controller {

    /**
     *
     */
    public function query() {
        $branch_data = $this->branch_model->getCachedBranchData();
        $platforms   = $this->platform_model->getAll();

        $params = $this->getRequestParameters(array(
            'product'      => array(),
            'branch'       => array(),
            'version'      => array(),
            'platform'     => array(),

            'query_search' => 'signature',
            'query_type'   => 'contains',
            'query'        => '',
            'date'         => '',
            'range_value'  => '1',
            'range_unit'   => 'weeks',

            'do_query'     => FALSE
        ));

        if ($params['do_query'] !== FALSE) {
            $reports = $this->common_model->queryTopSignatures($params);
        } else {
            $reports = array();
        }

        // TODO: redirect if there's one resulting report signature group

        $this->setViewData(array(
            'params'  => $params,
            'reports' => $reports,

            'all_products'  => $branch_data['products'],
            'all_branches'  => $branch_data['branches'],
            'all_versions'  => $branch_data['versions'],
            'all_platforms' => $platforms
        ));

    }

}
