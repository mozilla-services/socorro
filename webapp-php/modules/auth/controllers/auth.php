<?php defined('SYSPATH') OR die('No direct access allowed.');
/**
 * Handles all basic Auth pages. Based on the default Kohana Auth module.
 *
 * @package    	Authzilla
 * @author     	Ryan Snyder <ryan@foodgeeks.com>
 * @version		v.0.1
 */
class Auth_Controller extends Template_Controller {
	
	/**
	* Used to store the authenticated user.
	*
	* @see 		User
	* @access	public
	* @var		object	User
	*/
	public $authenticated_user;
	
	/**
	* @see 		Template
	* @access	public
	* @var		object	Template
	*/
	public $template;
	
	/**
	* Class constructor.  Instantiate the Template and Database classes.
	*
	* @access	public
	* @return	void
	*/
	public function __construct()
	{
		$this->template = Kohana::config('config.template');
		parent::__construct();
		
		$this->authenticated_user = Auth::instance()->get_user();
		$this->template->authenticated_user = (isset($this->authenticated_user->username) && !empty($this->authenticated_user->username)) ? $this->authenticated_user->username : null;			
		$this->template->body_class = 'ltr '; 
	}
	
	/**
	* Display the change email address page.
	*
	* @access	public
	* @return	void
	*/
	public function email()
	{
		Auth::instance()->login_required();
		$user = Auth::instance()->get_user();

		if (isset($_POST['action_change_email'])) {
			if ($user->change_email($_POST)) {
				url::redirect(url::site('verify?from=email', 'http'));
			} else {
				client::messageSendKohana($_POST->errors());
			}
		}
	
		$this->template->title = 'Change your Email Address';
		$this->template->content = new View('email');
		$this->template->content->current_email = $user->email; 
		$this->template->content->form_url = url::site('email', 'http');
	}
	
	/**
	* Display the forgot password page.
	*
	* @access	public
	* @return	void
	*/
	public function forgot()
	{
		if (Auth::instance()->logged_in()) {
			url::redirect(url::site('password', 'http'));
		}		
		
		if (isset($_POST['action_send_link']) && $this->validate_token()) {
			$user = new User_Model;
			if ($user->forgot_password($_POST['email'])) {
				url::redirect(url::site('verify?from=forgot', 'http'));
			} else {
				client::messageSend(Kohana::lang('auth.auth_no_accounts_associated_with_email'), E_USER_WARNING);
			}
		}

		$this->template->title = 'Request a Reset Password link';
		$this->template->content = new View('forgot');
		$this->template->content->form_url = url::site('forgot', 'http');
	}
	
	/**
	* Display the login page.
	*
	* @access	public
	* @return	void
	*/
	public function login()
	{
		// If user is already logged-in, send back to home page.
		if (Auth::instance()->logged_in()) {
			client::messageSend(Kohana::lang('auth.auth_already_logged_in'), E_USER_WARNING);
			url::redirect(url::site('', 'http'));
		}

		// Handle the login post submit
		if (isset($_POST['action_login']) && $this->validate_token()) {
			$user = new User_Model;
			if ($user->login($_POST)) {
				client::messageSend(Kohana::lang('auth.auth_login_success'), E_USER_NOTICE);
				url::redirect(session::instance()->get("requested_url"));
			} else {
				client::messageSend(Kohana::lang('auth.auth_login_fail'), E_USER_WARNING);
			}
		}
		
		// Record the users' last page for redirecting purposes, if applicable.
		if (isset($_SERVER['HTTP_REFERER']) && !empty($_SERVER['HTTP_REFERER']) && !strstr($_SERVER['HTTP_REFERER'], 'login')) {
			session::instance()->set("requested_url", $_SERVER['HTTP_REFERER']);
		}
		
		$this->template->title = 'Log In';
		$this->template->content = new View('login');
		$this->template->content->form_url = url::site('login', 'https');
		$this->template->content->username = (isset($_POST['username']) && !empty($_POST['username'])) ? $_POST['username'] : null;
		$this->template->content->password = (isset($_POST['password']) && !empty($_POST['password'])) ? $_POST['password'] : null;		
		$this->template->content->remember = (isset($_POST['remember']) && !empty($_POST['remember'])) ? $_POST['remember'] : null;		
	}

	/**
	* Log the user out and redirect to the home page.
	*
	* @access	public
	* @return	void
	*/
	public function logout()
	{
		Auth::instance()->logout();
		client::messageSend(Kohana::lang('auth.auth_logout_success'), E_USER_NOTICE);
		url::redirect("login");
	}
	
	/**
	* Display the change password page.
	*
	* @todo 	Request and verify current password.
	* @access	public
	* @return	void
	*/
	public function password()
	{
		Auth::instance()->login_required();

		if (isset($_POST['action_change_password'])) {
			$user = Auth::instance()->get_user();
			if ($user->change_password($_POST)) {
				client::messageSend(Kohana::lang('auth.auth_password_changed'), E_USER_NOTICE);
				url::redirect(url::site('password', 'http'));
			} else {
				client::messageSendKohana($_POST->errors());
			}
		}
		
		$this->template->title = 'Change your Password';
		$this->template->content = new View('password');
		$this->template->content->form_url = url::site('password', 'https');
	}
	
	/**
	* Display the account registration page.
	*
	* @access	public
	* @return	void
	*/
	public function register()
	{
		// If already logged in, redirect to home page.
		if (Auth::instance()->logged_in()) {
			url::redirect(url::site('', 'http'));
		}		
		
		// Handle the $_POST
		if (isset($_POST['action_create']) && $this->validate_token()) {
			if (!Captcha::instance()->valid($this->input->post('captcha_response'))) {
				client::messageSend(Kohana::lang('auth.auth_registration_captcha_invalid'), E_USER_WARNING);
			} 
			elseif($this->input->post('terms_agree') != 1) {
				client::messageSend(Kohana::lang('auth.auth_registration_terms_agree_required'), E_USER_WARNING);
			} 
			else {
				$user = new User_Model();
				if ($user->validate($_POST)) {
					$user->register();
					url::redirect(url::site('verify?from=registration', 'http'));
				} else {
					client::messageSendKohana($_POST->errors());
				}
			}
		}
		
		$this->template->title = 'Join ' . Kohana::config('config.site_name');
		$this->template->content = new View('register');
		$this->template->content->form_url = url::site('register', 'https');		
		$this->template->content->username = (isset($_POST['username']) && !empty($_POST['username'])) ? $_POST['username'] : null;
		$this->template->content->email = (isset($_POST['email']) && !empty($_POST['email'])) ? $_POST['email'] : null;
		$this->template->content->email_confirm = (isset($_POST['email_confirm']) && !empty($_POST['email_confirm'])) ? $_POST['email_confirm'] : null;
		$this->template->content->password = (isset($_POST['password']) && !empty($_POST['password'])) ? $_POST['password'] : null;				
		$this->template->content->password_confirm = (isset($_POST['password_confirm']) && !empty($_POST['password_confirm'])) ? $_POST['password_confirm'] : null;
		$this->template->content->terms_agree = (isset($_POST['terms_agree']) && !empty($_POST['terms_agree'])) ? true : false;		
	}
	
	
	/**
	* Validate a token from a submitted form.  If invalid, throw a 503 error.
	*
	* @access	private
	* @return	void
	*/
	private function validate_token()
	{
		if (isset($_POST) && !empty($_POST)) {
			if (empty($_POST['token']) || empty($_SESSION['token']) || ($_POST['token'] !== $_SESSION['token'])) {
				 url::redirect('verify_fail', 403);
			} else {
				return TRUE;
			}
		}
		return FALSE;
	}

	/**
	* Handle the account and email verification.
	*
	* @access	public
	* @return	void
	*/
	public function verify()
	{
		// User is attempting to reset password.  Handle in separate method.
		if (isset($_POST['action_reset_password'])) {
			 $this->verify_reset_password();
		} 

		// Attempt to verify the token sent in the URI.  If invalid, show fail screen.
		elseif (isset($_GET['token'])) { 	
			if ($action = Verification_Model::instance()->verify($_GET['token'])) {
				switch($action) {
					case 'email':
						client::messageSend(Kohana::lang('auth.auth_email_verified'), E_USER_NOTICE);
						url::redirect(url::site('', 'http'));
						break;
					case 'forgot':
						$this->verify_reset_password();
						break;
					case 'registration':
						client::messageSend(Kohana::lang('auth.auth_registration_email_verified'), E_USER_NOTICE);
						url::redirect(url::site(Kohana::config('auth.registration_success_uri'), 'http'));
						break;
				}
			} else {
				$this->verify_fail(); 
			}
		} 
		
		// If no token, assume that action is required.
		else {
			$this->verify_action_required();
		}
	}
	
	/**
	* Display the action required page to notify the user of the action they need to take.
	*
	* @access	public
	* @param 	string
	* @return	void
	*/
	public function verify_action_required($action='registration') 
	{
		if (isset($_GET['from']) && !empty($_GET['from'])) {
			$action = $_GET['from'];
		}
		
		switch($action) {
			case 'email':
				$this->template->content = new View('verify_action_required_email');		
				break;
			case 'forgot':
				$this->template->content = new View('verify_action_required_forgot');
				break;
			case 'registration':
			case 'default':
				$this->template->content = new View('verify_action_required_registration');
				break;
		}
	}
	
	/**
	* Display the reset password page once the token verification has passed.
	*
	* @access	public
	* @return	void
	*/
	public function verify_reset_password()
	{
		if (isset($_POST['action_reset_password'])) {
			if (isset($_POST['token']) && !empty($_POST['token'])) {
				if ($token = Verification_Model::instance()->verification_get($_POST['token'])) {

					// Token is valid.  Let's try to reset the password.
					$user = new User_Model($token->users_id);
					if ($user->reset_password($_POST)) {
						client::messageSend(Kohana::lang('auth.auth_reset_password_success'), E_USER_NOTICE);
						url::redirect(url::site('', 'http'));
					} 
					
					// Password did not match, show reset password page.
					else {
						$this->template->title = 'Reset your Password';
						$this->template->content = new View('verify_reset_password');
						$this->template->content->form_url = url::site('verify', 'https');		
						$this->template->content->token = (isset($_POST['token']) && !empty($_POST['token'])) ? $_POST['token'] : null;
						client::messageSendKohana($_POST->errors());
					}
				} 
				
				// Token failed.  Show failed verification page.
				else {
					$this->verify_fail();
				}
			} 	
			
			// No $_POST['token]. Fail.
			else {
				$this->verify_fail();
			}
		} 

		// Show reset password page.
		else {
			$this->template->title = 'Reset your Password';
			$this->template->content = new View('verify_reset_password');
			$this->template->content->form_url = url::site('verify', 'https');		
			$this->template->content->token = (isset($_GET['token']) && !empty($_GET['token'])) ? $_GET['token'] : null;
		}
	}

	/**
	* If the token verification failed, show this page.
	*
	* @access	public
	* @return	void
	*/
	public function verify_fail()
	{
		$this->template->title = 'Verification Failed';
		$this->template->content = new View('verify_fail');		
	}

	/* */
	
}