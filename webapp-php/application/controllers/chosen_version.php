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
 * While using Socorro UI, there is always a currently "Chosen" product
 * at a specific version. A user may have selected multiple products and versions
 * in which case we pick just one of them. This chosen one is used
 * to populate menu items like Trend Reports.
 *
 * This non-visual controller allows for switching the current state, which
 * is stored in a cookie.
 */
class Chosen_Version_Controller extends Controller 
{
  
    const URL = 'chosen_version/update/';
   /**
    * Sets the chosen version cookie and redirects to the
    * query string parameter 'url'
    * Example: /chosen_version/update/Firefox/3.5?url=query%2Fquery%3Fproduct%3DFirefox%26version%3DFirefox%253A3.5%26date%3D%26range_value%3D1%26range_unit%3Dweeks%26query_search%3Dsignature%26query_type%3Dexact%26query%3D
    * Updates the user's 
    */
    public function update($product, $version)
    {
        $params = $this->getRequestParameters(array('url' => url::base()));
	$url = $params['url'];
        $pvs = $this->branch_model->getProductVersions();

	$valid = FALSE;
	foreach ($pvs as $prod_vers) {
	  if (trim($version) == $prod_vers->version &&
	      trim($product) == $prod_vers->product) {
	          $valid = TRUE;
	          break;
	  }
	}
	if ($valid) {
            $this->navigationChooseVersion(trim($product), trim($version));
	} else {
	    Kohana::log('error', "Unable to update to choosen product $product version $version redirecting to $url anyways");
	}
	return url::redirect($url);
    }
}

?>