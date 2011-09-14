<?php defined('SYSPATH') OR die('No direct access allowed.');
/**
 * User authorization library. Handles user login and logout, as well as secure
 * password hashing.
 *
 * @package    Auth
 * @author     Kohana Team
 * @copyright  (c) 2007 Kohana Team
 * @license    http://kohanaphp.com/license.html
 */
class Auth_Core {

	// Session instance
	protected $session;

	// Configuration
	protected $config;

	/**
	 * Create an instance of Auth.
	 *
	 * @return  object
	 */
	public static function factory($config = array())
	{
		return new Auth($config);
	}

	/**
	 * Return a static instance of Auth.
	 *
	 * @return  object
	 */
	public static function instance($config = array())
	{
		static $instance;

		// Load the Auth instance
		empty($instance) and $instance = new Auth($config);

		return $instance;
	}

	/**
	 * Loads Session and configuration options.
	 *
	 * @return  void
	 */
	public function __construct($config = array())
	{
		// Append default auth configuration
		$config += Kohana::config('auth');

		// Clean up the salt pattern and split it into an array
		$config['salt_pattern'] = preg_split('/,\s*/', Kohana::config('auth.salt_pattern'));

		// Save the config in the object
		$this->config = $config;

		// Set the driver class name
		$driver = 'Auth_'.$config['driver'].'_Driver';

		Kohana::log('info', "loading driver " . $driver);

		if ( ! Kohana::auto_load($driver))
			throw new Kohana_Exception('core.driver_not_found', $config['driver'], get_class($this));

		Kohana::log('info', "driver loaded");

		// Load the driver
		$driver = new $driver($config);

		if ( ! ($driver instanceof Auth_Driver))
			throw new Kohana_Exception('core.driver_implements', $config['driver'], get_class($this), 'Auth_Driver');

		// Load the driver for access
		$this->driver = $driver;

		Kohana::log('debug', 'Auth Library loaded');
	}

	/**
	 * Check if there is an active session. Optionally allows checking for a
	 * specific role.
	 *
	 * @param   string   role name
	 * @return  boolean
	 */
	public function logged_in($role = NULL)
	{
	    return $this->driver->logged_in($role);
	}

	/**
	 * Check if there is an active session.  Optionally allows checking for a
	 * specific role. If not logged-in, or not logged-in with an appropriate
	 * role, redirect the user to the login page.
	 *
	 * @param   string   role name
	 * @return  boolean
	 */
	public function login_required($role = NULL) {
		if ($this->logged_in($role)) {
			return true;
		} else {
			if ($this->logged_in()) {
				client::messageSend(Kohana::lang('auth.auth_login_required_insufficient_rights'), E_USER_WARNING);
				url::redirect(url::site('', 'http'));
			} else {
				client::messageSend(Kohana::lang('auth.auth_login_required_not_logged_in'), E_USER_WARNING);
				session::instance()->set("requested_url", "/" . url::current());
				url::redirect(url::site('login', $this->config['proto']));
			}
		}
	}

	/**
	 * Returns the currently logged in user, or FALSE.
	 *
	 * @return  mixed
	 */
	public function get_user()
	{
		return $this->driver->get_user();
	}

	/**
	 * Attempt to log in a user by using an ORM object and plain-text password.
	 *
	 * @param   string   username to log in
	 * @param   string   password to check against
	 * @param   boolean  enable auto-login
	 * @return  boolean
	 */
	public function login($username, $password, $remember = FALSE)
	{
		if (empty($password))
			return FALSE;

		if (is_string($password))
		{
			// Get the salt from the stored password
			$salt = $this->find_salt($this->driver->password($username));

			// Create a hashed password using the salt from the stored password
			$password = $this->hash_password($password, $salt);
		}

		return $this->driver->login($username, $password, $remember);
	}

	/**
	 * Attempt to automatically log a user in.
	 *
	 * @return  boolean
	 */
	public function auto_login()
	{
		return $this->driver->auto_login();
	}

	/**
	 * Force a login for a specific username.
	 *
	 * @param   mixed    username
	 * @return  boolean
	 */
	public function force_login($username)
	{
		return $this->driver->force_login($username);
	}

	/**
	 * Log out a user by removing the related session variables.
	 *
	 * @param   boolean  completely destroy the session
	 * @return  boolean
	 */
	public function logout($destroy = FALSE)
	{
	    return $this->driver->logout($destroy);
	}

	/**
	 * Creates a hashed password from a plaintext password, inserting salt
	 * based on the configured salt pattern.
	 *
	 * @param   string  plaintext password
	 * @return  string  hashed password string
	 */
	public function hash_password($password, $salt = FALSE)
	{
		if ($salt === FALSE)
		{
			// Create a salt seed, same length as the number of offsets in the pattern
			$salt = substr($this->hash(uniqid(NULL, TRUE)), 0, count($this->config['salt_pattern']));
		}

		// Password hash that the salt will be inserted into
		$hash = $this->hash($salt.$password);

		// Change salt to an array
		$salt = str_split($salt, 1);

		// Returned password
		$password = '';

		// Used to calculate the length of splits
		$last_offset = 0;

		foreach ($this->config['salt_pattern'] as $offset)
		{
			// Split a new part of the hash off
			$part = substr($hash, 0, $offset - $last_offset);

			// Cut the current part out of the hash
			$hash = substr($hash, $offset - $last_offset);

			// Add the part to the password, appending the salt character
			$password .= $part.array_shift($salt);

			// Set the last offset to the current offset
			$last_offset = $offset;
		}

		// Return the password, with the remaining hash appended
		return $password.$hash;
	}

	/**
	 * Perform a hash, using the configured method.
	 *
	 * @param   string  string to hash
	 * @return  string
	 */
	public function hash($str)
	{
		return hash($this->config['hash_method'], $str);
	}

	/**
	 * Finds the salt from a password, based on the configured salt pattern.
	 *
	 * @param   string  hashed password
	 * @return  string
	 */
	public function find_salt($password)
	{
		$salt = '';

		foreach ($this->config['salt_pattern'] as $i => $offset)
		{
			// Find salt characters, take a good long look...
			$salt .= $password[$offset + $i];
		}

		return $salt;
	}

} // End Auth
