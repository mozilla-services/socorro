<?php defined('SYSPATH') or die('No direct script access.');
/**
 *
 */
class Report_Controller extends Controller {

    /**
     *
     */
    public function do_list() {

        $branch_data = $this->branch_model->getCachedBranchData();
        $platforms   = $this->platform_model->getAll();

        $params = $this->getRequestParameters(array(
            'signature'    => '',

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

        $reports = $this->common_model->queryReports($params);
        $builds  = $this->common_model->queryFrequency($params);

        $this->setViewData(array(
            'params'  => $params,
            'reports' => $reports,
            'builds'  => $builds,

            'all_products'  => $branch_data['products'],
            'all_branches'  => $branch_data['branches'],
            'all_versions'  => $branch_data['versions'],
            'all_platforms' => $platforms
        ));
    }

    /**
     * Fetch and display a single report.
     */
    public function index($uuid) {

        $report = $this->report_model->getByUUID($uuid);

        $this->setViewData(array(
            'report'  => $report
        ));
    }

    /**
     *
     */
    public function find() {

        echo "NOT IMPLEMENTED";

    }

}
