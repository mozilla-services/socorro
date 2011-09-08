<?php defined('SYSPATH') or die('No direct script access.');
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

require_once(Kohana::find_file('libraries', 'versioncompare', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'release', TRUE, 'php'));

/**
 * Common code between query and home controllers. Prepares data for query form.
 * NOTE: This is not a 'helper' in the sense of Kohana's helper classes (static 
 * methods to be used from the view)
 */
class QueryFormHelper
{
    
    /**
     * Prepare the branch and platform data for the view.
     *
     * @param   Model   The Branch Model
     * @param   Model   The Platform Model
     * @return  array   An array consisting of all of the products, branches, versions, versions by product and platforms.
     */
    public function prepareCommonViewData($branch_model, $platform_model)
    {
        $branch_data = $branch_model->getBranchData();
        $platforms   = $platform_model->getAll();

        $versions_by_product = array();
        foreach($branch_data['products'] as $product){
	        $versions_by_product[$product] = array();      
	    }
	    $versions_by_product_reversed = $versions_by_product;

	    foreach($branch_data['versions'] as $version){
            array_push($versions_by_product[$version->product], $version);
	    }

        $versions_by_product_reversed = array();
        foreach ($versions_by_product as $product => $versions) {
            $versions_by_product_reversed[$product] = array_reverse($versions);
        }

        return array(
            'all_products'  => $branch_data['products'],
            'all_branches'  => $branch_data['branches'],
            'all_versions'  => $branch_data['versions'],
            'versions_by_product'  => $versions_by_product,
            'all_platforms' => $platforms
        );
    }

    /**
     * Prepare the branch and platform data for the view.
     *
     * @param   Model   The Branch Model
     * @return  array   An array of versions ordered by product
     */
    public function prepareAllProducts($branch_model)
    {
        $branch_data = $branch_model->getBranchData();
	$versionCompare = new VersioncompareComponent();
        $versions_by_product = array();
        foreach($branch_data['products'] as $product){
	        $versions_by_product[$product] = array();      
	}
	foreach($branch_data['versions'] as $version){
            array_push($versions_by_product[$version->product], $version->version);
	}
        foreach ($versions_by_product as $versions) {
            $versionCompare->sortAppversionArray($versions);
        }

        return $versions_by_product;
    }

    /**
     * Given an array with the format product to version list,
     * this function will return an array of the current released 
     * versions of each products.
     * 
     * @param array - Input Example: {'Firefox': ['3.5', '3.0.10'], ...}
     * @return array - 
     * Output Example: {'Firefox': {'major': '3.5', 
     *                              'milestone': '3.5b99',
     *                              'development': '3.6pre'} ...}
     */
    public function currentProducts($products2versions)
    {
        $current = array();
	    $release = new Release;
        foreach ($products2versions as $product => $versions) {
	    if (count($versions) > 0) {
	        foreach (array_reverse($versions) as $v) {
	  	        $release_type = $release->typeOfRelease($v);
		        if (
		            ! array_key_exists($product, $current) ||
			        ! array_key_exists($release_type, $current[$product])
			        ) {
		                $current[$product][$release_type] = $v;
		            }
	            }
	        }
        }
	    uksort($current, 'strcasecmp');
	    return $current;
    }

}
