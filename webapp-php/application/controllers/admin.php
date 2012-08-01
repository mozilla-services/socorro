<?php defined('SYSPATH') OR die('No direct access allowed.');
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

 require_once(Kohana::find_file('models', 'os_matches_model'));
 require_once(Kohana::find_file('models', 'os_names_model'));

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
        if ($this->auth_is_active) {
            Auth::instance()->login_required(); // Login required will be enough for now
            Session::instance()->regenerate();
        }

        $this->js = html::script(array('js/jquery/date.js',
            'js/jquery/plugins/ui/jquery-ui-1.8.16.custom.min.js',
            'js/socorro/utils.js',
            'js/socorro/admin.js',
        ));

        $this->css = html::stylesheet(array(
            'css/flora/flora.tabs.css',
            'css/jquery-ui-1.8.16/flick/jquery-ui-1.8.16.custom.css'
        ), 'screen');
    }

    /**
     * Display the branch data sources admin page.
     *
     * @access public
     * @return void
     */
    public function branch_data_sources()
    {
                $product = $this->chosen_version['product'];

                // Flush cache for featured and unfeatured versions.
                $this->prepareVersions(true);

                $branch_data = $this->branch_model->getBranchData(false, true, true);

                $this->setView('admin/branch_data_sources');
                $this->setViewData(
                        array(
                                'products_list' => $this->branch_model->getProducts(),
                                'products' => $branch_data['products'],
                                'platforms'        => Kohana::config('platforms.platforms'),
                                'release_channels' => Kohana::config('release_channels.channels'),
                                'versions' => $branch_data['versions'],
                                'missing_visibility_entries' => $this->branch_model->getProductVersionsWithoutVisibility(),
                                'non_current_versions' => $this->branch_model->getNonCurrentProductVersions(true),
                                'default_start_date' => date('Y-m-d'),
                                'default_end_date' => date('Y-m-d', (time()+7776000)), // time() + 90 days
                                'throttle_default' => Kohana::config('daily.throttle_default'),
                                'url_base' => url::site('products/'.$product),
                                'url_nav' => url::site('products/'.$product)
                        )
                );
    }


    public function os_names()
    {
        $os_names_model = new OS_Name_Model();

        if (isset($_POST['action_add_os_name'])) {
            $os_name = trim($_POST['os_name']);
            $os_short_name = trim($_POST['os_short_name']);
            if (!empty($os_name) && !empty($os_short_name)) {
                $os_names_model->add($os_name, $os_short_name);
            }
        } elseif (isset($_POST['action_delete_os_name'])) {
            $os_name = trim($_POST['os_name']);
            $os_short_name = trim($_POST['os_short_name']);
            $os_names_model->delete($os_name, $os_short_name);
        }

        $os_names_data = $os_names_model->getData();
        $this->setView('admin/os_names');
        $this->setViewData(
            array(
                'os_names' => $os_names_data
            )
        );
    }


    public function os_matches()
    {
        $os_matches_model = new OS_Match_Model();
        $os_names_model = new OS_Name_Model();

        if (isset($_POST['action_add_os_match'])) {
            $os_family = trim($_POST['os_family']);
            $pattern = trim($_POST['pattern']);
            if (!empty($os_family) && !empty($pattern)) {
                $os_matches_model->add($os_family, $pattern);
            }
        } elseif (isset($_POST['action_delete_os_match'])) {
            $os_family = trim($_POST['os_family']);
            $pattern = trim($_POST['pattern']);
            $os_matches_model->delete($os_family, $pattern);
        }

        $os_matches_data = $os_matches_model->getData();
        $os_names_data = $os_names_model->getData();
        $this->setView('admin/os_matches');
        $this->setViewData(
            array(
                'os_name_matches' => $os_matches_data,
                'os_names' => $os_names_data
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
        $resp = $service->get("${host}/emailcampaigns/campaign/rawurlencode(${campaign_id})", 'json');
        if (! $resp) {
            client::messageSend("Error loading recent email campaigns", E_USER_ERROR);
        } else {
            $csrf_token = text::random('alnum', 32);
            $session = Session::instance();
            $session->set('csrf_token', $csrf_token);
            $this->setViewData(array('csrf_token' => $csrf_token));
            $this->setViewData(array('campaign' => $resp->campaign));
            $this->setViewData(array('counts' => $resp->counts));
        }
    }

    /**
     * Display the email form
     *
     * @access public
     * @return void
     */
    public function email()
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

        $resp = $service->get("${host}/emailcampaigns/campaigns/page/1", 'json');
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

        $p = rawurlencode($product);
        $v = rawurlencode(str_replace(' ', '', $versions));
        $sig = rawurlencode($signature);
        $s_date = rawurlencode($this->_convertDateForBackend($start_date));
        $e_date = rawurlencode($this->_convertDateForBackend($end_date));

        return  $service->get("${host}/emailcampaigns/volume/p/${p}/v/${v}/sig/${sig}/start/${s_date}/end/${e_date}", 'json');
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
            $data['csrf_token'] = text::random('alnum', 32);
            $session = Session::instance();
            $session->set('csrf_token', $data['csrf_token']);
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
     * Saves campaign
     *
     * @access public
     * @return void
     */
    public function save_campaign()
    {
        $author = Auth::instance()->get_user();
        $params = $this->_validateEmailCampaign();
        $data = $params->as_array();

        if ($params->validate()) {
            if ('Cancel' == $data['submit']) {
                // We'll re-display admin/email populated with $data
                $campaigns = array();
                $resp = $this->_recentCampaigns();
                if ($resp) {
                    $campaigns = $resp->campaigns;
                }
                $data['campaigns'] = $campaigns;
            } else {
                $session = Session::instance();
                $token = $session->get('csrf_token');
                if (strlen($token) > 0 && $token == $params['token']) {
                    // retrieve # of emails
                     $resp = $this->_saveCampaign(
                        $params['email_product'], $params['email_versions'],
                        $params['email_signature'],
                        $params['email_subject'], $params['email_body'],
                        $params['email_start_date'], $params['email_end_date'],
                        $author
                     );

                    if ($resp) {
                        client::messageSend("Campaign saved" . $resp->campaign_id, E_USER_NOTICE);
                        return url::redirect('/admin/email_campaign/' . $resp->campaign_id);
                    } else {
                        Kohana::log('error', "No Response");
                        client::messageSend("Unknown systems error. Investigate before trying again.", E_USER_ERROR);
                        return url::redirect('admin/email');
                    }
                } else {
                    Kohana::log('alert', "CSRF token didn't match session[" . $token .
                                         "] params[" . $params['token'] . "]");
                    return url::redirect('admin/email');
                }
            }
        } else {
            Kohana::log('error', 'Form did not validate');
            $data['has_errors'] = true;
            $data['errors'] = $params->errors('email_form_errors');
        }
        $data['products'] = $this->branch_model->getProducts();
        $this->setView('admin/email'); // Back that thing up
        $this->setViewData($data);
    }

    /**
     * Helper method uses Hoopsnake API to create
     * an email campaign.
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
    private function _saveCampaign($product, $versions, $signature, $subject, $body, $start_date, $end_date, $author)
    {
        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $service = new Web_Service($config);
        $host = Kohana::config('webserviceclient.socorro_hostname');

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

        return $service->post("${host}/emailcampaigns/create", $data, 'json');

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
        $params = new Validation($this->input->post(array(), null, true));
        $data = $params->as_array();

        if ($params->validate()) {
            $session = Session::instance();
            $token = $session->get('csrf_token');
            if (strlen($token) > 0 && $token == $params['token']) {
                // retrieve # of emails
                $status = $data['submit'];
                if ($status == 'start' || $status == 'stop') {
                    $resp = $this->_sendEmail(
                        $params['campaign_id'],
                        $author,
                        $status
                    );
                    if ($resp) {
                        client::messageSend(json_encode($resp), E_USER_NOTICE);
                    }
                }
            } else {
                Kohana::log('alert', "CSRF token didn't match session[" . $token .
                                     "] params[" . $params['token'] . "]");
                return url::redirect('admin/email');
            }
        } else {
            Kohana::log('error', 'Form did not validate');
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
     * @param string $campaign_id   Campaign ID to send
     * @param string $author        Username of the currently logged in admin
     * @param string $status        Change status of campaign (start|stop)
     *
     * @return JSON response or FALSE if there is an error
     */
    private function _sendEmail($campaign_id, $author, $status)
    {
        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $service = new Web_Service($config);
        $host = Kohana::config('webserviceclient.socorro_hostname');

        $data = array(
            'campaign_id' => $campaign_id,
            'status' => $status,
            'author' => $author
            );

        return $service->post("${host}/email", $data, 'json');
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
        $date_regex = '/^[0-9]{2}\/[0-9]{2}\/[0-9]{4}$/';
        $date_invalid = true;
        $val = $validation[$field];
        if (preg_match($date_regex, $val)) {
            list($year, $month, $day) = $this->_splitDate($val);
            if (checkdate($month, $day, $year)) {
                $date_invalid = false;
            }
        }
        if ($date_invalid) {
            $validation->add_error($field, 'valid_date');
        } else {
            $raw_start = trim($validation['email_start_date']);
            $raw_end   = trim($validation['email_end_date']);
            if ('email_end_date' == $field && preg_match($date_regex, $raw_start)) {
                $start = strtotime($this->_convertDateForBackend($raw_start));
                $end   = strtotime($this->_convertDateForBackend($raw_end));
                if ($start > $end) {
                    $validation->add_error($field, 'end_before_start_date');
                }
            }
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
        $valid_variables = array('*|UNSUBSCRIBE_URL|*', '*|EMAIL_ADDRESS|*', '*|CRASH_DATE|*', '*|CRASH_URL|*');

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

    public function add_product()
    {
        $default_params = array('product' => '', 'version' => '', 'release_channel' => '', 'build_id' => '',
                                'platform' => '', 'repository' => '', 'beta_number' => '');
        $params = $this->getRequestParameters($default_params);
        $response = $this->branch_model->add($params['product'], $params['version'], $params['release_channel'], $params['build_id'],
                                $params['platform'], $params['repository'], $params['beta_number']);
        $json_response;
        if ($response === TRUE) {
            $json_response->{'status'} = 'success';
            $json_response->{'message'} = 'Product version was successfully added.';
        } else {
            $json_response->{'status'} = 'failed';
            $json_response->{'message'} = 'Error: ' . $response;
        }
        echo json_encode($json_response);
        exit;
    }

    public function update_featured_versions() {
        $get = $this->parseQueryString();
        $data = array();

        foreach($get as $name => $value) {
            $data[$name] = implode(",", $value);
        }

        echo json_encode($this->branch_model->update_featured_versions($data));
        exit;
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
}
