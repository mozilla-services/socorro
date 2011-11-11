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

if (Kohana::config('config.enable_hooks') == FALSE) {
    include_once(Kohana::find_file('vendor', 'recaptchalib'));
}

/**
 * Allows users control over their email preferences
 *
 * Authentication is via a Token and thus very weak.
 *
 * @category Controller
 * @package  EmailSubscription
 * @author   Austin King <ozten@mozilla.com>
 *
 */
class Email_Controller extends Controller
{
    /**
     * Kohana request handler
     *
     * @param string $subscribeToken Each email address has an associated token
     *
     * @return HTML Response
     */
    public function subscription($subscribeToken)
    {
        $subscriptionStatus = true;
        $token = urlencode($subscribeToken);
        $backendError = false;
        $success = $this->input->get('success', false);
        list($recaptchaErrorCode, $recaptchaError) =
            $this->_recaptchaError($this->input->get('recaptcha_error', 'false'));
        $unknownToken = false;
        // update_status can redirect here with token set to unknown
        if ($subscribeToken == 'unknown') {
            $unknownToken = true;
        } else {
            list($host, $service) = $this->_webService();
            $resp = $service->get(
                "${host}/emailcampaigns/subscription/${token}", 'json'
            );
            if ($resp) {
                if ('true' == $resp->found) {
                    $subscriptionStatus = $resp->status;
                } else {
                    $unknownToken = true;
                }
            } else {
                $backendError = true;
            }
        }
        $this->setViewData(
            array('backend_error'      => $backendError,
                  'unknown_token'      => $unknownToken,
                  'token'              => $subscribeToken,
                  'status'             => $subscriptionStatus,
                  'recaptchaError'     => $recaptchaError,
                  'recaptchaErrorCode' => $recaptchaErrorCode,
                  'success'            => $success,
            ));
    }

    /**
     * Kohana request handler
     *
     * @return redirects
     */
    public function update_status()
    {
        $token = 'unknown';
        $recaptchaError = false;
        $success = false;
        if ($_POST) {
            $token = $this->input->post('token', $token);
            if (recaptcha::check()) {
                $validation = new Validation($this->input->post(array(), null, true));
                $validation->add_rules('token',            'required', 'length[36]');
                $validation->add_rules('subscribe_status', 'required');

                if ($validation->validate()) {
                    $data = $validation->as_array();
                    $token = $data['token'];

                    if ('true' == $data['subscribe_status']) {
                        $status = 'true';
                    } else {
                        $status = 'false';
                    }

                    $backend_data = array(
                        'token'  => $token,
                        'status' => $status,
                        );
                    list($host, $service) = $this->_webService();
                    $resp = $service->post("${host}/emailcampaigns/subscription/${token}", $backend_data, 'json');
                    if ($resp) {
                        $success = 'true';
                    } else {
                        client::messageSend("Unable to save your update", E_USER_ERROR);
                    }
                }
            } else {
                /* will be error code name, mapped in _recaptchaError to error messages */
                $recaptchaError = recaptcha::error();
            }
        } else {
            // Hacking form isn't user editable...
            url::redirect("email/subscription/" . urlencode($token));
        }
        $params = array();
        if ($recaptchaError) {
            array_push($params, "recaptcha_error=" . urlencode($recaptchaError));
        }
        if ($success) {
            array_push($params, "success=true");
        }
        url::redirect("email/subscription/" . urlencode($token) . "?" . implode('&', $params));
    }


    /**
     * Helper method for preparing a web service library
     *
     * @return an instance of Web_Service
     */
    private function _webService()
    {
        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }
        $service = new Web_Service($config);
        $host = Kohana::config('webserviceclient.socorro_hostname');
        return array($host, $service);
    }

    /**
     * Maps ReCAPTCHA error codes to copy
     *
     * @param string $errorCode ReCaptcha error code
     *
     * @return array Two item array list($errorCode, $message)
     *         errorCode is either null or the ReCaptcha error code
     *         message is user friendly copy
     */
    private function _recaptchaError($errorCode)
    {
        switch ($errorCode) {
            case 'incorrect-captcha-sol':
                return array($errorCode, "Words didn't match the image, please try again.");
            default:
                return array(null, null);
        }
    }
}
