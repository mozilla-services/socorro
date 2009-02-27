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

/**
 * Common code between query and home controllers. Prepares data for query form.
 */
class WidgetDataHelper
{
    /**
     returns strucutre like
     array(
        "Firefox"     => array("major", "milestone", "development"),
        "Thunderbird" => array("milestone", "development"),
        "SeaMonkey"   => array("milestone", "development")
	);
     */
    public function convertProductToReleaseMap($mtbfReports)
    {
        $prodToRelease = array();
	foreach ($mtbfReports as $report) {
   	    $product = $report->product;
	    if ( ! array_key_exists($product, $prodToRelease)) {
	      $prodToRelease[$product] = array();
	    }
	    array_push($prodToRelease[$product], $report->release);
	}
	return $prodToRelease;
    }

    public function convertProductToVersionMap($topcrashbyurl)
    {
        $prodToVersion = array();
	foreach ($topcrashbyurl as $report) {
	    if ($report->enabled) {
   	        $product = $report->product;
	        if ( ! array_key_exists($product, $prodToVersion)) {
	            $prodToVersion[$product] = array();
	        }
	        array_push($prodToVersion[$product], $report->version);
	    }
	}
	return $prodToVersion;
    }

    public function convertArrayProductToVersionMap($products)
    {
        $prodToVersion = array();
	foreach ($products as $product => $releases) {

	    if ( ! array_key_exists($product, $prodToVersion)) {
	        $prodToVersion[$product] = array();
	    }
	    $versions = array();
	    foreach ($releases as $release) {
	      array_push($versions, $release->version);
	    }
	    $prodToVersion[$product] =  $versions;

	}
	return $prodToVersion;
    }

    public function featuredReleaseOrValid($product, $allMtbfs, $featuredMtbfs)
    {
      return $this->_featuredOrValid($product, $allMtbfs, $featuredMtbfs, 'release');
    }

    public function featuredVersionOrValid($product, $allMtbfs, $featuredMtbfs)
    {
      return $this->_featuredOrValid($product, $allMtbfs, $featuredMtbfs, 'version');
    }

    private function _featuredOrValid($product, $allMtbfs, $featuredMtbfs, $member)
    {
        $validReleases = $allMtbfs[$product];
	if (count($validReleases) == 0) {
	  throw new Exception("Invalid argument, no valid $member for inputs $product " . 
			      var_dump($allMtbfs));
	}
        foreach ($featuredMtbfs as $i => $feature) {
	    if ($feature['product'] == $product) {
  	        if (in_array($feature[$member], $validReleases)){
		    return $feature[$member];
	        } else {
		    Kohana::log('alert', "Bad config for MTBF $product there is no $member that matches the Database.");
		    break;
		}
	    }
        }      
	return $allMtbfs[$product][0];
    }
}
?>