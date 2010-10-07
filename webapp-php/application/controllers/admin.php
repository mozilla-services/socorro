<?php defined('SYSPATH') OR die('No direct access allowed.');
/* **** BEGIN LICENSE BLOCK *****
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
 * ***** END LICENSE BLOCK ***** 
 *
 */

/**
 * Handles all Admin related pages.
 *
 * TODO - This screen is one of the few read/write webservices. Our current
 *        cache clearing strategy is to not cache. This page is used 
 *        infrequently. If it becomes an issue, we should change Web_Services
 *        to have a more predictable cache key and do proper caching for the 
 *        three web service calls below.
 *
 * @package    SocorroUI
 * @subpackage Controllers
 * @author     Ryan Snyder <ryan@foodgeeks.com>
 * @version    v.0.2
 */
class Admin_Controller extends Controller 
{
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
                $this->js = html::script(array('js/jquery/date.js',
                                               'js/jquery/plugins/ui/jquery.datePicker.js',
                                               'js/socorro/admin.js',
                                               ));
                $this->css = '<link href="' . url::base() . 'css/datePicker.css" rel="stylesheet" type="text/css" media="screen" />';
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

    /**
     * Kohana handler
     * TODO: Web Service data is paginated, use next, previous, etc 
     *
     * @return HTML repsonse
     */
    public function email_campaign($id)
    {
        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $service = new Web_Service($config);
        $host = Kohana::config('webserviceclient.socorro_hostname');
        $campaign_id = intval($id);
        $one_hour_cache = 60 * 60;
        $resp = $service->get("${host}/201009/email/campaign/${campaign_id}", 'json', $one_hour_cache);
        if (! $resp) {
            client::messageSend("Error loading recent email campaigns", E_USER_ERROR);
        } else {
            $this->setViewData(array('campaign' => $resp->campaign));
        }        
    }

    /**
     * Display the email form
     *
     * @access public
     * @return void
     */
    public function email ()
    {
        $campaigns = array();
        $resp = $this->_recentCampaigns();
        if ($resp) {
            $campaigns = $resp->campaigns;
        }

        $this->setViewData(array(
            'email_product' => '',
            'email_versions' => '',
            'email_signature' => '',
            'email_subject' => '',
            'email_body' => "Paste Email Message here.\n\n*|UNSUBSCRIBE_URL|*",
            'email_start_date' => '',
            'email_end_date' => '',
            'campaigns' => $campaigns,
            'products' => $this->branch_model->getProducts(),
        ));              
    }

    /**
     * Helper method retrieves recent campaigns
     * 
     * @return JSON object or FALSE if there wasn an error
     */
    private function _recentCampaigns()
    {
        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $service = new Web_Service($config);
        $host = Kohana::config('webserviceclient.socorro_hostname');
        
        $resp = $service->get("${host}/201009/email/campaigns/page/1", 'json');
        if (! $resp) {
            client::messageSend("Error loading recent email campaigns", E_USER_ERROR);
        }
        return $resp;
    }

    /**
     * Helper method estimates number of emails that will
     * be sent by calling the Hoopsnake layer
     * @param string $product    The Product
     * @param string $signature  A Crash Signature
     * @param string $start_date A datePicker compatible date (DD/MM/YYY)
     * @param string $end_date   A datePicker compatible date (DD/MM/YYY)
     *
     * @return JSON object or FALSE if there is a communication error
     */
    private function _emailVolume($product, $versions, $signature, $start_date, $end_date)
    {
        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $service = new Web_Service($config);
        $host = Kohana::config('webserviceclient.socorro_hostname');

        $p = urlencode($product);
        $v = urlencode(str_replace(' ', '', $versions));
        $sig = urlencode($signature);
        $s_date = urlencode($this->_convertDateForBackend($start_date));
        $e_date = urlencode($this->_convertDateForBackend($end_date));

        return  $service->get("${host}/201009/email/volume/p/${p}/v/${v}/sig/${sig}/start/${s_date}/end/${e_date}", 'json');
    }

    /**
     * Confirms the admin's choice to send an email
     *
     * @access public
     * @return void
     */
    public function confirm_email()
    {
        $campaigns = array();
        $resp = $this->_recentCampaigns();
        if ($resp) {
            $campaigns = $resp->campaigns;
        }

        $params = $this->_validateEmailCampaign();
        $data = $params->as_array();
        $data['campaigns'] = $campaigns;
        if ($params->validate()) {
            $resp = $this->_emailVolume(
                $params['email_product'],
                $params['email_versions'],
                $params['email_signature'],
                $params['email_start_date'],
                $params['email_end_date']
            );
            if ($resp) {
                $est_emails = $resp->emails;
            } else {
                $data['has_errors'] = true;
                $data['errors'] = array('connection' => "Unknown Server Error, please try again in a few minutes");
                $est_emails = 0;
            }
            $data['estimated_count'] = number_format($est_emails);
        } else {
            $data['has_errors'] = true;
            $data['products'] = $this->branch_model->getProducts();
            $data['errors'] = $params->errors('email_form_errors');
            $this->setView('admin/email');
        }
        $this->setViewData($data);
    }

    /**
     * Helper method prepares an instance of the Validation 
     * library
     * 
     * @return object
     */
    private function _validateEmailCampaign() 
    {
        $validation = new Validation($this->input->post(array(), null, true));
        $validation->pre_filter('trim');
        $validation->add_rules('email_signature', 'length[2, 255]');
        $validation->add_rules('email_versions',  'required');
        $validation->add_rules('email_subject',   'required', 'length[3, 140]');
        $validation->add_rules('email_body',      'required', 'length[3, 8014]');

        $validation->add_callbacks('email_start_date', array($this, 'validDate'));
        $validation->add_callbacks('email_end_date',   array($this, 'validDate'));

        $validation->add_callbacks('email_body',   array($this, 'validVariables'));

        return $validation;
    }


    /**
     * Sends email
     *
     * @access public
     * @return void
     */
    public function send_email()
    {
        $author = Auth::instance()->get_user();
        $params = $this->_validateEmailCampaign();
        $data = $params->as_array();

        if ($params->validate()) {
            if ('Cancel' == $data['submit']) {
                // We'll re-display admin/email populatd with $data
                $campaigns = array();
                $resp = $this->_recentCampaigns();
                if ($resp) {
                    $campaigns = $resp->campaigns;
                }
                $data['campaigns'] = $campaigns;
            } else {
                // retrieve # of emails
                $resp = $this->_sendEmail(
                    $params['email_product'], $params['email_versions'],
                    $params['email_signature'],
                    $params['email_subject'], $params['email_body'],
                    $params['email_start_date'], $params['email_end_date'],
                    $author
                );
                if ($resp) {
                    client::messageSend("Email Sent " . $resp->emails->actual_count, E_USER_NOTICE);
                    return url::redirect('admin/email'); 
                } else {
                    Kohana::log('error', "No Response");
                    client::messageSend("Unknown systems error. Investigate before trying again.", E_USER_ERROR);
                    return url::redirect('admin/email'); 
                }
            }
        } else {
            $data['has_errors'] = true;
            $data['errors'] = $params->errors('email_form_errors');
        }
        $data['products'] = $this->branch_model->getProducts();
        $this->setView('admin/email'); // Back that thing up
        $this->setViewData($data);
    }
    /**
     * Helper method uses Hoopsnake API to create
     * an email campaign and send the emails.
     *
     * @param string $product    A product
     * @param string $signature  A Crash Signature
     * @param string $subject    The Subject line of the email
     * @param string $body       The Body of the email
     * @param string $start_date A datePicker compatible date (DD/MM/YYY)
     * @param string $end_date   A datePicker compatible date (DD/MM/YYY)
     * @param string $author     Username of the currently logged in admin
     *
     * @return JSON response or FALSE if there is an error
     */
    private function _sendEmail($product, $versions, $signature, $subject, $body, $start_date, $end_date, $author)
    {
        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $service = new Web_Service($config);
        $host = Kohana::config('webserviceclient.socorro_hostname');
        $cache_in_minutes = Kohana::config('webserviceclient.topcrash_vers_rank_cache_minutes', 60);
        $lifetime = $cache_in_minutes * 60; // Lifetime in seconds

        $data = array(
            'product' => $product,
            'versions' => $versions,
            'signature' => $signature,
            'subject' => $subject,
            'body' => $body,
            'start_date' => $this->_convertDateForBackend($start_date),
            'end_date' => $this->_convertDateForBackend($end_date),
            'author' => $author
            );

        return $service->post("${host}/201009/email", $data, 'json');

    }

    /* Custom Validation */
    /**
     * Validaton callback compatible with JS datePicker
     * format. 
     *
     * @param object $validation An instance of Validation
     * @param string $field      The form field
     * 
     * @return void
     */
    public function validDate($validation, $field)
    {
        $date_invalid = true;
        $val = $validation[$field];
        if (preg_match('/^[0-9]{2}\/[0-9]{2}\/[0-9]{4}$/', $val)) {
            list($year, $month, $day) = $this->_splitDate($val);
            if (checkdate($month, $day, $year)) {
                $date_invalid = false;
            }
        }
        if ($date_invalid) {
            $validation->add_error($field, 'valid_date');
        }
    }

    /**
     * Validation Callback.
     *
     * The email body must have a variable which will be replaced with
     * the opt-out url. Optionally it may have other variables.
     *
     * The backend will swap these variables out with personalized
     * values.
     * 
     * @param object $validation The validator
     * @param string $field      The field being evaluated
     *
     * @return void
     */
    public function validVariables($validation, $field)
    {
        $unsubscribe_seen = false;

        $body = $validation['email_body'];
        $variables = array();

        //First element must be the unsubscribe url, as it's required and we check for it below
        $valid_variables = array('*|UNSUBSCRIBE_URL|*', '*|EMAIL_ADDRESS|*');

        $count = preg_match_all('/\*\|[a-zA-Z_ ]*\|\*/', $body, $variables);

        if (0 < $count) {
            for ($i = 0; $i < $count; $i++) {
                $var = $variables[0][$i];
                if (in_array($var, $valid_variables)) {
                    if ($var == $valid_variables[0]) {
                        $unsubscribe_seen = true;
                    }
                } else {
                    $validation->add_error($field, 'valid_unknown_variable');
                }
            }
        }
        if (! $unsubscribe_seen) {

            $validation->add_error($field, 'valid_no_unsubscribe');
        } 
    }

    /**
     * Helper method for parsing JS datePicker style Dates
     * 
     * @param string $date A date Example: 28/04/2010
     *
     * @return A three element array list($year, $month, $day)
     */
    private function _splitDate($date)
    {
        $day   = intval(substr($date, 0, 2));
        $month = intval(substr($date, 3, 2));
        $year  = intval(substr($date, 6, 4));
        return array($year, $month, $day);
    }

    /**
     * Simple conversion from frontend friendly date format to 
     * backend friendly format
     * 
     * @param staring $adate A JS datePicker formatted date Example: 04/28/2010
     *
     * @return string suitable for Hoopsnake call (YYYY-MM-DD) Example: 2010/04/28
     */
    private function _convertDateForBackend($adate) 
    {
        list($year, $month, $day) = $this->_splitDate($adate);
        $m = $month;
        if ($month < 10) {
            $m = "0${month}";
        }
        $d = $day;
        if ($day < 10) {
            $d = "0${day}";
        }
        return "${year}-${m}-${d}";
    }

    /* */
}
