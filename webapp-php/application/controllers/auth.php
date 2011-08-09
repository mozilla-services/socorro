<?php defined('SYSPATH') OR die('No direct access allowed.');
/**
 * Handles LDAP based Authentication. Based on the default Kohana Auth module
 * as well Ryan Snyder's AuthZilla Controller
 * 
 * To Disable Authentication, use the NoAuth driver in conf/auth.php
 * 
 * To use File or ORM for Authentication, remove this controller or copy files from
 * modules/auth/controller as well as modules/auth/view and customize them to your
 * application's needs.
 *
 * @author     	Austin King <aking@mozilla.com>
 */
class Auth_Controller extends Controller {

    /**
     * Constructs an instance of Auth_Controller.
     * Disables rendering as Auth is a non-visual controller
     */
    public function __construct()
    {
        parent::__construct();
        $this->auto_render = FALSE;
    }

     /**
      * Attempt login via LDAP Authentication
      */
     public function login()
     {
         url::site('auth/login', Kohana::config('auth.proto'));
         
         $this->sensitivePageHTTPSorRedirectAndDie('/auth/login');
	 $this->_setReferrerButIgnore('auth/login');
	 if (Auth::instance()->logged_in()) {
	     client::messageSend(Kohana::lang('auth_already_logged_in'), E_USER_WARNING);
	     url::redirect($this->_getReferrerOrUse('home/dashboard'));
	 } else {
	     // LDAP driver will prompt for username, password. remember feature isn't supported
	     if (Auth::instance()->login('not_used','not_used')) {
		 client::messageSend(Kohana::lang('auth.auth_login_success'), E_USER_NOTICE);
		 url::redirect($this->_getReferrerOrUse('home/dashboard'));
	     } 
	 }
     }

     /**
      * Record the user's last page for redirecting purposes, if applicable.
      * Ignore the Referrer and use the homepage if it's the same as $cur_path.
      *
      * @param $cur_path - avoid recursion should be the current path 'auth/login' etc
      */
     private function _setReferrerButIgnore($cur_path)
     {
	 if (isset($_SERVER['HTTP_REFERER']) && !empty($_SERVER['HTTP_REFERER']) && !strstr($_SERVER['HTTP_REFERER'], $cur_path)) {	
	     Session::instance()->set("requested_url", $_SERVER['HTTP_REFERER']);
	 } else {
	     Session::instance()->set("requested_url", url::site());
	 }
     }

    /**
     * Gets the user's last page for redirecting purposes.
     * 
     * @param string $default path or url if no referrer is in the session
     * @return string a path or url suitable for url::redirect
     */
     private function _getReferrerOrUse($default)
     {
        $requested_url = Session::instance()->get("requested_url", $default);
        if (Kohana::config('auth.proto') == 'https') {
            $requested_url = url::site($requested_url, 'https');
        }
        return $requested_url;
     }

     /**
      * Log the user out and redirects them back to the homepage
      *
      * @access	public
      * @return	void
      */
     public function logout()
     {
         $this->sensitivePageHTTPSorRedirectAndDie('/auth/logout');
	 $auth = Auth::instance();
	 if (method_exists($auth->driver, 'ldap_logout')) {
	     $auth->driver->ldap_logout();
	 }
	 $auth->logout(TRUE);
	 client::messageSend(Kohana::lang('auth.auth_logout_success'), E_USER_NOTICE);
	 url::redirect(url::site());
     }
}