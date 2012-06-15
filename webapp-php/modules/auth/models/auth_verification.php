<?php defined('SYSPATH') OR die('No direct access allowed.');

class Auth_Verification_Model extends Model {

	/**
	 * Allow verification tokens to have a TTL of 1 day.
	 */
	const TOKEN_TTL = 86400;

	/**
	 * Set the current timestamp for use throughout this class.
	 */
	protected $now;

	/**
	 * Set the timestamp at which the token is considered expired.
	 */
	protected $expired;

	/**
	* @see 		Database
	* @access	protected
	* @var		object	Database
	*/
 	protected $db;

	/**
	* Class constructor.  Instantiate database and initiate garbage collection.
	*
	* @access	public
	* @return	void
	*/
	public function __construct($token=null)
	{
		$this->db = new Database;
		$this->now = time();
		$this->expired = $this->now - self::TOKEN_TTL;

		// Initiate garbage collection
		if (mt_rand(1, 100) === 1) {
			$this->verifications_delete_expired();
		}
	}

	/**
	 * Return a static instance of this Model.
	 *
	 * @return  object
	 */
	public static function instance()
	{
		static $instance;
		empty($instance) and $instance = new Verification_Model();
		return $instance;
	}

	/**
	 * Finds a new unique token, using a loop to make sure that the token does
	 * not already exist in the database. This could potentially become an
	 * infinite loop, but the chances of that happening are very unlikely.
	 *
	 * @access 	public
	 * @param 	int
	 * @param 	string	options 'email', 'registration'
	 * @param 	string 	optional Email address - used for changing email address
	 * @return  string
	 */
	public function verification_create($users_id, $action, $email=null)
	{
		while (TRUE)
		{
			$token = text::random('alnum', 32);
			if ($this->db->select('token')->where('token', $token)->get('verifications')->count() === 0)
			{
				$this->db->insert('verifications',
					array(
						'token' => $token,
						'users_id' => $users_id,
						'action' => $action,
						'email' => $email,
						'created' => $this->now
					)
				);
				return $token;
			}
		}
	}

	/**
	 * Delete a specific token after it has been used.
	 *
	 * @access	public
	 * @param 	string
	 * @return  void
	 */
	private function verification_delete($token)
	{
		$this->db->where(array('token' => $token))->delete('verifications');
		return $this;
	}

	/**
	 * Fetch a specific token.
	 *
	 * @access	public
	 * @param 	string
	 * @return  void
	 */
	public function verification_get($token)
	{
		$verifications = $this->db->where(array('token' => $token, 'created >' => $this->expired))->get('verifications');
		if (isset($verifications[0]->token) && !empty($verifications[0]->token)) {
			return $verifications[0];
		}
		return false;
	}

	/**
	 * Delete all expired tokens.
	 *
	 * @access	private
	 * @return  void
	 */
	private function verifications_delete_expired()
	{
		$this->db->where('created <', ($this->expired))->delete('verifications');
		$this->db->where(array('created <' => $this->expired, 'verified' => '0'))->delete('users'); // @todo Move this to a more appropriate place
	}

	/**
	 * Verify that a token has been set and has not expired.
	 *
	 * @access	public
	 * @param 	string
	 * @param 	string	options 'email', 'registration'
	 * @return  array
	 */
	public function verify($token)
	{
		if ($verification = $this->verification_get($token)) {
			if (isset($verification->users_id) && !empty($verification->users_id)) {
				switch ($verification->action) {
					case 'email':
						// Delete token.
						$this->verification_delete($token);
						return $this->verify_email($verification->users_id, $verification->email);
						break;
					case 'forgot':
						// Do not delete token yet.  Still need this.
						return $this->verify_forgot();
						break;
					case 'registration':
						// Delete token.
						$this->verification_delete($token);
						return $this->verify_registration($verification->users_id);
						break;
				}
			}
		}
		return false;
	}

	/**
	 * The user has verified their email address, update use record to reflect this update.
	 *
	 * @access	private
	 * @return  bool
	 */
	private function verify_email ($id, $email) {
		$user = new User_Model($id);
		$user->email = $email;
		$user->save();

		return 'email';
	}

	/**
	 * The user has verified their email address, now allow the user to reset their password.
	 *
	 * @access	private
	 * @return  bool
	 */
	private function verify_forgot () {
		return 'forgot';
	}

	/**
	 * Mark the user as verified, set the user's role to 'login' and auto-login this user.  Then
	 * send out a welcome email.
	 *
	 * @access	private
	 * @return  bool
	 */
	private function verify_registration ($id) {
		$user = new User_Model($id);
		$user->verified = 1;
		$user->save();

		$this->db->insert('roles_users', array('user_id' => $id, 'role_id' => 1));
		Auth::instance()->force_login($user->username);
		$user->register_welcome_email();

		return 'registration';
	}

	/* */
}
