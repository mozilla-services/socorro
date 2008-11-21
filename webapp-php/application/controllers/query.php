<?php defined('SYSPATH') or die('No direct script access.');
require_once dirname(__FILE__).'/../libraries/MY_SearchReportHelper.php';
/**
 *
 */
class Query_Controller extends Controller {

    /**
     *
     */
    public function query() {
        $helper = new SearchReportHelper();
        $branch_data = $this->branch_model->getBranchData();
        $platforms   = $this->platform_model->getAll();

        $params = $this->getRequestParameters($helper->defaultParams());
	Kohana::log('info', Kohana::debug($params));
        $helper->normalizeParams( $params );

        cachecontrol::set(array(
            'etag'     => $params,
            'expires'  => time() + ( 60 * 60 )
        ));

        if ($params['do_query'] !== FALSE) {
            $reports = $this->common_model->queryTopSignatures($params);
        } else {
            $reports = array();
        }

        // TODO: redirect if there's one resulting report signature group

        $this->setViewData(array(
            'params'  => $params,
            'queryTooBroad' => $helper->shouldShowWarning(),
            'search_helper' => $helper,
            'reports' => $reports,

            'all_products'  => $branch_data['products'],
            'all_branches'  => $branch_data['branches'],
            'all_versions'  => $branch_data['versions'],
            'all_platforms' => $platforms
        ));

    }

}
