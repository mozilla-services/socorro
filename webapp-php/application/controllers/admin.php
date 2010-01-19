<?php defined('SYSPATH') OR die('No direct access allowed.');
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
				if ($rv = $this->branch_model->add(
                        trim($_POST['product']), 
                        trim($_POST['version']), 
                        trim($_POST['branch']), 
                        trim($_POST['start_date']), 
                        trim($_POST['end_date'])
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
				if ($rv = $this->branch_model->update(
                    trim($_POST['update_product']), 
                    trim($_POST['update_version']), 
                    trim($_POST['update_branch']),
                    trim($_POST['update_start_date']), 
                    trim($_POST['update_end_date']) 
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
		
 		$this->setView('admin/branch_data_sources');	
		$this->setViewData(
			array(
				'branches' => $branch_data['branches'],
				'products' => $branch_data['products'],
				'versions' => $branch_data['versions'],
				'missing_entries' => $this->branch_model->findMissingEntries(),
				'missing_visibility_entries' => $this->branch_model->getProductVersionsWithoutVisibility(),
				'default_start_date' => date('Y-m-d'),
				'default_end_date' => date('Y-m-d', (time()+7776000)) // time() + 90 days
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
 		$this->setView('admin/index');	
    }

    /* */
}
