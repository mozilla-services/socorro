<?php defined('SYSPATH') or die('No direct script access.');
require_once dirname(__FILE__).'/../libraries/MY_SearchReportHelper.php';
require_once dirname(__FILE__).'/../libraries/MY_QueryFormHelper.php';
/**
 *
 */
class Query_Controller extends Controller {

    /**
     *
     */
    public function query() {
      //Query Form Stuff
        $searchHelper = new SearchReportHelper;
        $queryFormHelper = new QueryFormHelper;

	$queryFormData = $queryFormHelper->prepareCommonViewData($this->branch_model, $this->platform_model);
	$this->setViewData($queryFormData);

	//Current Query Stuff
        $params = $this->getRequestParameters($searchHelper->defaultParams());
        $searchHelper->normalizeParams( $params );

        cachecontrol::set(array(
            'etag'     => $params,
            'expires'  => time() + ( 60 * 60 )
        ));
        
        if ($params['do_query'] !== FALSE) {
            $reports = $this->common_model->queryTopSignatures($params);
        } else {
            $reports = array();
        }

	//common getParams
	//prepareAndSetCommonViewData($params)

        // TODO: redirect if there's one resulting report signature group


        $this->setViewData(array(
            'params'  => $params,
            'queryTooBroad' => $searchHelper->shouldShowWarning(),
            'reports' => $reports
	 ));


    }

}
