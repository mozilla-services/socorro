<?php defined('SYSPATH') OR die('No direct access allowed.');
/**
 * Client functions for redirecting and for sending notices and warnings to the user.
 *
 * @package    	CreativeCollective
 * @author     	Ryan Snyder
 * @version		v.0.1
 */
class client {

	/**
	 * Retrieves messages intended for the user/client from a lower level function.
	 * This is part of a message passing system which provides standard methods
	 * for lower level functions to pass messages to the client (such as failed
	 * input validation, etc).
	 *
	 * @see		self::clientMessageSend
	 * @access	public
	 * @static
	 * @return	string	HTML output of user messages
	 */
	public static function messageFetchHtml()
	{
		if ($messages = Session::instance()->get_once('client_messages')) {

			$notices  = '';
			$warnings = '';
			$errors   = '';
			foreach ($messages as $message) {
				switch ($message[1]) {
					case E_USER_WARNING:
						$warnings .= '<li>'.$message[0].'</li>'."\n";
						break;
					case E_USER_ERROR:
						$errors .= '<li">'.$message[0].'</li>'."\n";
						break;
					case E_USER_NOTICE:
					default:
						$notices .= '<div id="message" class="success"><h2>' . $message[0] . '</h2></div>'."\n";
						break;
				}
			}

			$message_html = '';
			if (!empty($warnings) || !empty($errors)) {
				$message_html .= '
					<div id="message" class="error">
				  		<h2>Uh oh! Something went wrong...</h2>
						<ul>
							' . $warnings . $errors . '
						</ul>
					</div>
				';
			}

			if (!empty($notices)) {
				$message_html .= $notices;
			}

			if (!empty($message_html)) {
				return $message_html;
			}
		}
	}

	/**
	 * Stores a message intended for the user/client from a lower level function.
	 * This is part of a message passing system which provides standard methods
	 * for lower level functions to pass messages to the client (such as failed
	 * input validation, etc).
	 *
	 * @see		self::messagesFetchHtml()
	 * @access	public
	 * @static
	 * @param	string	Message to pass to the client
	 * @param	int		Classification of message type - E_USER_WARNING, E_USER_ERROR, E_USER_NOTICE
	 * @return	void
	 */
	public static function messageSend($feedback, $type)
	{
		$_SESSION['client_messages'][] = array($feedback, $type);
	}

	/**
	 * Stores a Kohana error array and prepares it for client display.
	 *
	 * @see		self::messagesFetchHtml()
	 * @access	public
	 * @static
	 * @param 	array 	An array of Kohana errors that are returned from Kohana Validation
	 * @param 	string 	The file and string prefix for the error.  For 'auth', requires i18n/auth.php,
	 *					which contains - 'auth_email_required' => 'An email address is required'.
	 * @return	void
	 */
	public static function messageSendKohana(array $errors, $type='auth')
	{
		if (is_array($errors) && !empty($errors)) {
			foreach ($errors as $key => $value) {
				$message = Kohana::lang($type . '.'  . $type ."_" . $key . '_' . $value);
				self::messageSend($message, E_USER_WARNING);
			}
		}
	}


	/* */
}
