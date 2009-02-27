<?php defined('SYSPATH') or die('No direct script access.');

require_once dirname(__FILE__).'/../libraries/MY_WidgetDataHelper.php';

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
 *   Austin King <aking@mozilla.com> (Original Author)
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
require_once dirname(__FILE__).'/../libraries/MY_SearchReportHelper.php';
require_once dirname(__FILE__).'/../libraries/MY_QueryFormHelper.php';
/**
 *
 */
class Home_Controller extends Controller 
{
    /**
     * SocorroUI homepage  is a Search form (query) and set of dashboard widgets
     */
    public function dashboard()
    {
        $helper = new SearchReportHelper();
        $queryFormHelper = new QueryFormHelper;

	$queryFormData = $queryFormHelper->prepareCommonViewData($this->branch_model, $this->platform_model);
	$this->setViewData($queryFormData);

	$versions_by_product = $this->getViewData('versions_by_product');

        $topcrashers = $this->topcrashers_model = new Topcrashers_Model();

        $params = $this->getRequestParameters($helper->defaultParams());

        cachecontrol::set(array(
            'etag'     => $params,
            'expires'  => time() + ( 60 * 60 )
        ));
        
        $mtbf = $this->_mtbf( new Mtbf_Model );

        $this->setViewData(array(
            'params'  => $params,
            'searchFormModel' => $params,
            'topcrashes'   => $this->_topCrashesBySig($topcrashers, $versions_by_product),
            'topcrashesbyurl' => $this->_topCrashesByUrl(),
	    'mtbf' => $mtbf,
            'mtbfChartRangeMax' => $this->_chartRangeMax($mtbf)
        ));
    }

    private function _chartRangeMax($mtbf)
    {
        $chartRangeMax = 10;
        foreach($mtbf as $m){
            foreach($m['crashes'] as $c){
                foreach($c['data'] as $datum){
  	            if( is_numeric($datum[1]) && $datum[1] > $chartRangeMax) {
		        $chartRangeMax = $datum[1];
	            }
		}
	    }
	}
	return $chartRangeMax;
    }

    private function _topCrashesBySig($topcrashers, $versions_by_product)
    {
        $sigSize = Kohana::config("dashboard.topcrashbysig_numberofsignatures");
        $featured = Kohana::config("dashboard.topcrashbysig_featured");

        $widget = new WidgetDataHelper;
        $prodToVersionMap = $widget->convertArrayProductToVersionMap($versions_by_product);
        $topcrashes = array();
        foreach ($prodToVersionMap as $product => $versions) {
  	    $version = $widget->featuredVersionOrValid($product, $prodToVersionMap, $featured);
            $data = $topcrashers->getTopCrashers($product, $version, null, null, $sigSize);
	    array_push($topcrashes, array(
	        'label' => "$product $version",
                'name' => $product,
                'version' => $version,
                'crashes' => $data[1], // 0 is last_updated time 1 is list of signatures and counts
                'other-versions' => $versions
            ));
        }
        return $topcrashes;
    }

    private function _topCrashesByUrl()
    {
        $widget = new WidgetDataHelper;
        $model = new TopcrashersByUrl_Model;
        $all_reports = $model->listReports();
        $prodToVersionMap = $widget->convertProductToVersionMap($all_reports);
        $featured = Kohana::config("dashboard.topcrashbyurl_featured");
        
        $data = array();
        $tmp = array();
        foreach ($prodToVersionMap as $product => $versions) {
	    $version = $widget->featuredVersionOrValid($product, $prodToVersionMap, $featured);
  	    $crashRes = $model->getTopCrashersByUrl($product, $version);
	    array_push($data, array(
                                    'label'     => "$product $version",
				    'name'    => $product,
				    'version' => $version,
				    'crashes' => array_slice($crashRes[2], 0, 3),
				    'other-versions' => $this->_findOtherReleases($all_reports, $product, 'version')
            ));
	}
	return $data;
    }

    private function _mtbf($model)
    {
        $widget = new WidgetDataHelper;
        $featured = Kohana::config("dashboard.mtbf_featured");
        $mtbfData = array();

        $mtbf_all_releases = $model->listReports();
        $prodToReleaseMap = $widget->convertProductToReleaseMap($mtbf_all_releases);
        
        foreach ($prodToReleaseMap as $product => $releases) {
  	    $release = $widget->featuredReleaseOrValid($product, $prodToReleaseMap, $featured);

	    $crashes = $model->getMtbfOf($product, $release);

	     array_push($mtbfData, array(
	     'label'       => "$product $release",
	     'product'  => $product,
             'release'   => $release,
             'crashes'  => $crashes,
	     'other-versions' => $releases //$this->_findOtherReleases($mtbf_all_releases, $mtbf['product'])
		));
        }
        return $mtbfData;
    }
    private function _findOtherReleases($mtbf_all_releases, $product, $prop='release')
    {
        $other = array();
        foreach($mtbf_all_releases as $i => $release){
	    if ($release->product == $product) {
	      array_push($other, $release->{$prop});
	    }
        }
	return $other;
    }
}