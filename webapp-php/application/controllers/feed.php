<?php
require_once(Kohana::find_file('libraries', 'MY_SearchReportHelper', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'moz_feed', TRUE, 'php'));
/**
 * Feeds for Socorro UI
 */
class Feed_Controller extends Controller {

  /**
   *
   * Bug#492017 - provide RSS feed of latest crashes
   */
    public function crashes_by_product($product, $version, $platform='ALL')
    {

        $db = new Common_Model;
        $searchHelper = new SearchReportHelper;
        $params = $searchHelper->defaultParams();
	$params['product'] = array($product);
	$params['version'] = array($product . ':' . $version);
	if ($platform != 'ALL') {
	    $params['platform'] = array($platform);
	}
	$params['range_value'] = '2';

	$reports = $db->queryReports($params);

	$this->auto_render = FALSE;

	$feed = moz_feed(url::base(),
			 url::current(TRUE),
			 "Mozilla $product $version $platform Recent Crashes",
			 $reports);
	header( 'Content-Type: ' . $feed['contentType'] . '; charset=utf-8' );
	echo $feed['xml'];
    }

  /**
   *
   * Bug#492017 - provide RSS feed of latest crashes
   */
    public function crashes_by_platform($platform='ALL')
    {
        $db = new Common_Model;
        $searchHelper = new SearchReportHelper;
        $params = $searchHelper->defaultParams();
	$params['product'] = array();

	$params['range_value'] = '2';
       	if ($platform != 'ALL') {
	    $params['platform'] = array($platform);
	}

	$reports = $db->queryReports($params);

	$this->auto_render = FALSE;

	$feed = moz_feed(url::site(),
			 url::current(TRUE),
			 "Mozilla $platform Recent Crashes",
			 $reports);
	header( 'Content-Type: ' . $feed['contentType'] . '; charset=utf-8' );
	echo $feed['xml'];
    }
}
?>
