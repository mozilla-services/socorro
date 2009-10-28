<?php defined('SYSPATH') OR die('No direct access allowed.');
class Auth_User_Model extends ORM {

	// Relationships
	protected $has_many = array('user_tokens');
	protected $has_and_belongs_to_many = array('roles');

	// Columns to ignore
	protected $ignored_columns = array('password_confirm');

	public function __set($key, $value)
	{
		if ($key === 'password')
		{
			// Use Auth to hash the password
			$value = Auth::instance()->hash_password($value);
		}

		parent::__set($key, $value);
	}

	/**
	 * Validates and optionally saves a new user record from an array.
	 *
	 * @param  array    values to check
	 * @param  boolean  save the record when validation succeeds
	 * @return boolean
	 */
	public function validate(array & $array, $save = FALSE)
	{
		$array = Validation::factory($array)
			->pre_filter('trim')
			->add_rules('email', 'required', 'length[1,127]', 'valid::email', array($this, 'email_available'))
			->add_rules('username', 'required', 'length[4,32]', 'chars[a-zA-Z0-9_]', array($this, 'username_available'))
			->add_rules('password', 'required', 'length[5,42]')
			->add_rules('password_confirm', 'matches[password]')
		;

		return parent::validate($array, $save);
	}

	/**
	 * Validates login information from an array, and optionally redirects
	 * after a successful login.
	 *
	 * @param  array    values to check
	 * @param  string   URI or URL to redirect to
	 * @return boolean
	 */
	public function login(array & $array, $redirect = FALSE)
	{
		$array = Validation::factory($array)
			->pre_filter('trim')
			->add_rules('username', 'required', 'length[4,127]')
			->add_rules('password', 'required', 'length[5,42]');

		// Login starts out invalid
		$status = FALSE;

		// Validate the user, then make sure the password matches.
		if ($array->validate()) {
			$this->find($array['username']);
			
			// User must have verified their email address and must have a status == 1 in order to login.
			if ($this->status == 1 && $this->verified == 1) {			
				$remember = (isset($array['remember']) && !empty($remember)) ? true : false;
				if ($this->loaded AND Auth::instance()->login($this, $array['password'], $remember)) {
					if (is_string($redirect)) {
						url::redirect($redirect);
					} 
					$status = TRUE;
				} else {
					$array->add_error('username', 'invalid');
				}
			}
		}

		return $status;
	}

	/**
	 * Validates an array for a matching password and password_confirm field.
	 *
	 * @param  array    values to check
	 * @param  string   save the user if
	 * @return boolean
	 */
	public function change_email(array & $array, $save = FALSE)
	{
		$array = Validation::factory($array)
			->pre_filter('trim')
			->add_rules('email', 'required', 'length[4,127]', 'valid::email', array($this, 'email_available'))
			->add_rules('email_confirm', 'matches[email]')			
		;

		if ($status = $array->validate()) {
			$token = Verification_Model::instance()->verification_create($this->id, 'email', $array['email']);
			$this->change_email_email($array['email'], $token);
		}

		return $status;
	}

	/**
	 * Send the change email email to the user.
	 *
	 * @param  string 	The user's new email address
	 * @param  token	The validation token  
	 * @return boolean
	 */
	public function change_email_email($email, $token)
	{
		$to = $email;
		$from_email = Kohana::config('auth.email');
		$from = Kohana::config('auth.site_name') . "<" . $from_email . ">";
		$subject = 'Email change notification for ' . Kohana::config('auth.site_name');

		$message = new View('emails/changeemail_email');
		$message->url = url::site() . 'verify?token=' . $token;
		$message->site_name = Kohana::config('auth.site_name');
		$message->username = $this->username;
		$message = $message->render();

		mail ($to, $subject, $message, 'From: ' . $from, '-f' . $from_email);
	}
	
	/**
	 * Validates an array for a matching password and password_confirm field.
	 *
	 * @todo Update to require the user's current password
	 * @param  array    values to check
	 * @param  string   save the user if
	 * @return boolean
	 */
	public function change_password(array & $array, $save = FALSE)
	{
		$array = Validation::factory($array)
			->pre_filter('trim')
			->add_rules('password', 'required', 'length[5,42]')
			->add_rules('password_confirm', 'matches[password]');

		if ($status = $array->validate())
		{
			// Change the user's password
			$this->password = $array['password'];
			$this->save();
			
			// Now force the user to logout and log back in, just in case.
			Auth::instance()->logout();
			Auth::instance()->force_login($this->username);
		}

		return $status;
	}
	
	/**
	 * Validate an email address for the forgot password form.  Create a record in the
	 * verifications table.  Send out an email with the token and link to reset
	 * the password. 
	 *
	 * @param  string    User's email address
	 * @return boolean
	 */
	public function forgot_password($email)
	{	
		if ($this->find(array('email' => $email))) {
			if ($this->email == $email) {
				$token = Verification_Model::instance()->verification_create($this->id, 'forgot');
				$this->forgot_password_email($email, $token);
				return true;
			}
		}
		return false;
	}
	
	/**
	 * Send the forgot password email to the user.
	 *
	 * @param  string   User's email address
	 * @param  token	The validation token  
	 * @return boolean
	 */
	public function forgot_password_email($email, $token)
	{
		$to = $email;
		$from_email = Kohana::config('auth.email');
		$from = Kohana::config('auth.site_name') . "<" . $from_email . ">";
		$subject = 'Password reset notification for  ' . Kohana::config('auth.site_name');

		$message = new View('emails/forgot_email');
		$message->url = url::site() . 'verify?token=' . $token;
		$message->site_name = Kohana::config('auth.site_name');
		$message->username = $this->username;
		$message = $message->render();

		mail ($to, $subject, $message, 'From: ' . $from, '-f' . $from_email);
	}

	/**
	 * User has been validated.  Completed the registration process by adding the new user 
	 * into the users table, and mail the user an email verification token.
	 *
	 * @param  string    User's email address
	 * @return boolean
	 */
	public function register() {
		$this->username = strtolower($this->username);
		$this->created = time();
		$this->save();

		$token = Verification_Model::instance()->verification_create($this->id, 'registration');
		$this->register_email($token);
		
		return true;
	}
	
	/**
	 * Send out the email verification link at the end of the registration process.
	 *
	 * @param  string    User's email address
	 * @return boolean
	 */
	public function register_email ($token)
	{
		$to = $this->email;
		$from_email = Kohana::config('auth.email');
		$from = Kohana::config('auth.site_name') . "<" . $from_email . ">";
		$subject = Kohana::config('auth.site_name') . ' registration';

		$message = new View('emails/register_email');
		$message->url = url::site() . 'verify?token=' . $token;
		$message->site_name = Kohana::config('auth.site_name');
		$message->username = $this->username;
		$message = $message->render();

		mail ($to, $subject, $message, 'From: ' . $from, '-f' . $from_email);	
	}
	
	/**
	 * Send out the welcome email once the registration process is complete and the 
	 * user has verified their email address.
	 *
	 * @return boolean
	 */
	public function register_welcome_email ()
	{
		$to = $this->email;
		$from_email = Kohana::config('auth.email');
		$from = Kohana::config('auth.site_name') . "<" . $from_email . ">";
		$subject = 'Welcome to the ' . Kohana::config('auth.site_name') . '!';

		$message = new View('emails/welcome_email');
		$message->url = url::site();
		$message->site_name = Kohana::config('auth.site_name');
		$message->username = $this->username;
		$message = $message->render();

		mail ($to, $subject, $message, 'From: ' . $from, '-f' . $from_email);
	}
	
	/**
	 * Validates an array for a matching password and password_confirm field.  If passes,
	 * save as the user's new password.
	 *
	 * @param  array    values to check
	 * @return boolean
	 */
	public function reset_password(array & $array)
	{
		$array = Validation::factory($array)
			->pre_filter('trim')
			->add_rules('password', 'required', 'length[5,42]')
			->add_rules('password_confirm', 'matches[password]');

		if ($status = $array->validate())
		{
			// Change the password
			$this->password = $array['password'];
			$this->save();
			
			// Now auto-login this user.
			Auth::instance()->force_login($this->username);
		}

		return $status;
	}

	/**
	 * Tests if a username exists in the database. This can be used as a
	 * Validation rule.
	 *
	 * @param   mixed    id to check
	 * @return  boolean
	 * 
	 */
	public function username_exists($id)
	{
		return $this->unique_key_exists($id);
	}

	/**
	 * Does the reverse of unique_key_exists() by returning TRUE if user id is available
	 * Validation rule.
	 *
	 * @param    mixed    id to check 
	 * @return   boolean
	 */
	public function username_available($username)
	{
		return ! $this->unique_key_exists($username);
	}

	/**
	 * Does the reverse of unique_key_exists() by returning TRUE if email is available
	 * Validation Rule
	 *
	 * @param string $email 
	 * @return void
	 */
	public function email_available($email)
	{
		return ! $this->unique_key_exists($email);
	}

	/**
	 * Tests if a unique key value exists in the database
	 *
	 * @param   mixed        value  the value to test
	 * @return  boolean
	 */
	public function unique_key_exists($value)
	{
		return (bool) $this->db
			->where($this->unique_key($value), $value)
			->count_records($this->table_name);
	}

	/**
	 * Allows a model to be loaded by username or email address.
	 */
	public function unique_key($id)
	{
		if ( ! empty($id) AND is_string($id) AND ! ctype_digit($id))
		{
			return valid::email($id) ? 'email' : 'username';
		}

		return parent::unique_key($id);
	}

} // End Auth User Model
