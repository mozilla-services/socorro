<?php defined('SYSPATH') OR die('No direct access allowed.');

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
 * Handles all Admin related pages.
 *
 * @package 	SocorroUI
 * @subpackage  Controllers
 * @author      Ryan Snyder <ryan@foodgeeks.com>
 * @version     v.0.1
 */
class Admin_Controller extends Controller {

    /**
    * Class constructor.  Instantiate the Template and Database classes.
    *
    * @access   public
    * @return   void
    */
    public function __construct()
    {
        parent::__construct();

        // Authentication with a role of 'admin' is required for every single page within this controller.
        // Auth::instance()->login_required('admin'); // Once more than admins are on the system, can probably switch to this
		Auth::instance()->login_required(); // Login required will be enough for now
		$this->js = html::script(array('js/socorro/admin.js'));
    }
    
    /**
     * Validate the 'featured' field for a product / version.   
     *
     * @bizrule A product may not have more than 3 featured versions.
     * @param string The product name
     * @param string The version name
     * @return void
     */
    private function _branch_data_sources_featured($product, $version)
    {
        $featured = 'f';
        if (
            (isset($_POST['featured']) && $_POST['featured'] == 't') || 
            (isset($_POST['update_featured']) && $_POST['update_featured'] == 't')
        ) {
            $featured = 't';
    	    if ($this->branch_model->getFeaturedVersionsExcludingVersionCount($product, $version) >= 3) {
    			client::messageSend("There are already 3 featured versions of this product. Set 1 of the featured products to not be featured, then try again.", E_USER_WARNING);
    	        $featured = 'f';
    	    }
        }
	    return $featured;
    }

    /**
     * Display the branch data sources admin page.
     *
     * @access public
     * @return void
     */
    public function branch_data_sources()
    {
		if (isset($_POST['action_add_version'])) {
			if (
				!empty($_POST['product']) && 
				!empty($_POST['version']) && 
				!empty($_POST['branch']) && 
				!empty($_POST['start_date']) &&
				!empty($_POST['end_date'])
			) {
                $featured = $this->_branch_data_sources_featured($_POST['product'], $_POST['version']);
				if ($rv = $this->branch_model->add(
                        trim($_POST['product']), 
                        trim($_POST['version']), 
                        trim($_POST['branch']), 
                        trim($_POST['start_date']), 
                        trim($_POST['end_date']),
                        $featured
                )) {
					client::messageSend("This new product/version has been added to the database.", E_USER_NOTICE);
					url::redirect('admin/branch_data_sources'); 
				} else {
					client::messageSend("There was an error adding this product/version to the database.", E_USER_WARNING);
				}
			} else {
				client::messageSend("You must fill in all of the fields.", E_USER_WARNING);
			}
		}
		elseif (isset($_POST['action_update_version'])) {
			if (
				!empty($_POST['update_product']) && 
				!empty($_POST['update_version']) && 
				!empty($_POST['update_branch']) && 
				!empty($_POST['update_start_date']) && 
				!empty($_POST['update_end_date'])
			) {
                $featured = $this->_branch_data_sources_featured($_POST['update_product'], $_POST['update_version']);
				if ($rv = $this->branch_model->update(
                    trim($_POST['update_product']), 
                    trim($_POST['update_version']), 
                    trim($_POST['update_branch']),
                    trim($_POST['update_start_date']), 
                    trim($_POST['update_end_date']),
                    $featured
                )) {
					client::messageSend("This product/version has been updated in the database.", E_USER_NOTICE);
					url::redirect('admin/branch_data_sources'); 					
				} else {
					client::messageSend("There was an error updating this product/version.", E_USER_WARNING);
				}
			} else {
				client::messageSend("You must fill in all of the fields.", E_USER_WARNING);
			}
		}
		elseif (isset($_POST['action_delete_version'])) {
			if (!empty($_POST['delete_product']) && !empty($_POST['delete_version'])) {
				if ($rv = $this->branch_model->delete(trim($_POST['delete_product']), trim($_POST['delete_version']))) {
					client::messageSend("This product/version has been deleted from the database.", E_USER_NOTICE);
					url::redirect('admin/branch_data_sources');					
				} else {
					client::messageSend("There was an error deleting this product/version.", E_USER_WARNING);
				}
			} else {
				client::messageSend("You must fill in all of the fields.", E_USER_WARNING);
			}
		}

		$branch_data = $this->branch_model->getBranchData(false, false);
        $product = $this->chosen_version['product'];
		
 		$this->setView('admin/branch_data_sources');	
		$this->setViewData(
			array(
				'branches' => $branch_data['branches'],
				'products' => $branch_data['products'],
				'versions' => $branch_data['versions'],
				'missing_entries' => $this->branch_model->findMissingEntries(),
				'missing_visibility_entries' => $this->branch_model->getProductVersionsWithoutVisibility(),
				'default_start_date' => date('Y-m-d'),
				'default_end_date' => date('Y-m-d', (time()+7776000)), // time() + 90 days
                'url_base' => url::site('products/'.$product),
                'url_nav' => url::site('products/'.$product)				
			)			
		);
    }

    /**
     * Display the admin index page.
     *
     * @access public
     * @return void
     */
    public function index ()
    {
        $product = $this->chosen_version['product'];

 		$this->setView('admin/index');	
		$this->setViewData(
			array(
                'url_base'                => url::site('products/'.$product),
                'url_nav'                 => url::site('products/'.$product)				
			)			
		); 		
    }

    /* */
}
