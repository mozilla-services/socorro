<?php defined('SYSPATH') OR die('No direct access allowed.');
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
 * Contributor(s):
 *   Austin King <aking@mozilla.com> (Original Author)
 *   Wilson Lee <wlee@mozilla.com> - LDAP code https://svn.mozilla.org/projects/phonebook/trunk
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

/**
 * LDAP Kohana Auth driver.
 * 
 * LDAP doesn't quite match the interface specified by the Auth library.
 * Instead of recieving username and password from an HTML form and then
 * hashing the password, this driver relies on the built-in browser 
 * Basic Authentication. Because of this the following methods are affected:
 * 
 * - login ignores the username and password parameters
 * - login doesn't support the $remember option
 * - password serves no purpose
 *
 * force_login acts as expected
 * 
 * ldap_logout is a new method called during the logout process to
 * clear LDAP credentials.
 * 
 * The Controller's job is very simple, to use the Auth library and 
 * redirect the user to resources. No forms, forgot your password, or
 * other features are needed.
 *
 * Design Decision: We could unpack PHP_AUTH_USER and PHP_AUTH_PW
 * at the controller level and pass them into Auth, but these values
 * would need to be passed through untouched as the real Auth work
 * is done by the backend Auth server. To keep things simple, and 
 * all LDAP related code in the same file, the Auth login is called
 * with dummy values for username, password, and remember.
 * 
 * We could also have forgone using Auth all together. Hopefully
 * using Auth will make it easy for other Socorro UI users to 
 * use NoAuth or Database backed authentication with little effort.
 *
 * @package    Auth
 */
class Auth_LDAP_Driver extends Auth_Driver {
    /**
     * Logs a user in.
     *
     * We don't need to support auto-login since the browser handels LDAP sessions
     *
     * @param   string   username IGNORED
     * @param   string   password IGNORED
     * @param   boolean  enable IGNORED
     * @return  boolean
     */
    public function login($username, $password, $remember)
    {
        if (!isset($_SERVER["PHP_AUTH_USER"])) {
	    $this->_ask_for_credentials();
  	    $this->_ask_for_credentials_and_exit();
        } else {
	    if ($this->_is_LDAP_login_successful($_SERVER["PHP_AUTH_USER"], $_SERVER["PHP_AUTH_PW"])) {
		  return $this->complete_login($_SERVER["PHP_AUTH_USER"]);
	    } else {
  	        $this->_ask_for_credentials_and_exit();
	    }
	}
    }

    /**
     * Forces a user to be logged in, without specifying a password.
     *
     * @param   mixed    username
     * @return  boolean
     */
    public function force_login($username)
    {
        // Complete the login
        return $this->complete_login($username);
    }

    /**
     * Get the stored password for a username.
     *
     * @param   mixed   username
     * @return  string
     */
    public function password($user)
    {
        //no-op
    }

    /**
     * Called from Auth_Controller to clear LDAP Credentials
     */
    public function ldap_logout()
    {
        header('HTTP/1.0 401 Unauthorized');
    }
    /**
     * Validates that the user input is a valid email address
     * @param string user
     * @return boolean
     */
    private function _check_valid_user($user) {
        return preg_match('/^[a-z]+@(.+?)\.(.+)$|^[a-z]+$/', $user);
    }

    /**
     * Prompt the user for Basic Auth Credentials via HTTP headers
     */
    private function _ask_for_credentials() {
	$realm = Kohana::config('ldap.realm', 'Mozilla Corporation - LDAP Login');
        header("WWW-Authenticate: Basic realm=\"$realm\"");
    }
    /**
     * Stop processing the current request and prompt user
     * for their credentials.
     *
     * Sends HTTP headers and then exists.
     */
    private function _ask_for_credentials_and_exit()
    {
        header('HTTP/1.0 401 Unauthorized');
        $this->_ask_for_credentials();
        print "<h1>401 Unauthorized</h1>";
        die;
    }

    /**
     * Checks with LDAP if the given username and password will
     * authenticate and if so will authorize.
     * @param string $username - a full email address
     * @param string password - plain text password
     * @return boolean TRUE for good credentials FALSE otherwise
     */
    private function _is_LDAP_login_successful($username, $password)
    {
        if ($this->_check_valid_user($_SERVER["PHP_AUTH_USER"])) {
	    // Shared LDAP access (not based on user's identity yet)
	    $bind_dn = Kohana::config('ldap.bind_dn');
	    $bind_pass = Kohana::config('ldap.bind_password');
	    $search_dn = Kohana::config('ldap.search_dn', 'dc=mozilla');
	    $user_filter = "mail=" . trim($_SERVER['PHP_AUTH_USER']);
	    return $this->_authenticate_and_authorize($bind_dn, $bind_pass, $search_dn, $user_filter);
        } else {
	    Kohana::log('debug', "Expected an email address, got " . $_SERVER["PHP_AUTH_USER"] . " skipping auth");
        }
	return FALSE;
    }

    /**
     * Searches for user in LDAP by email address and then attempts to 
     * authenticate them based on their password. Optionally if 
     * an authorization group is setup (ldap.admin_group) then it will
     * make sure the are authorized.
     * @param string $bind_dn - shared LDAP user
     * @param string $bind_pass - shared LDAP password
     * @param string $serach_dn - base dn used for searching for users
     * @param string $user_filter - search condition for finding the user's dn
     * @return boolean - TRUE if user can log in
     */
    private function _authenticate_and_authorize($bind_dn, $bind_pass, $search_dn, $user_filter)
    {
	set_error_handler(array($this, '_handle_errors'));
	$ldapconn = ldap_connect(Kohana::config("ldap.host"));
	$search_bind = ldap_bind($ldapconn, $bind_dn, $bind_pass);
	if($search_bind) {
	    $sr = ldap_search($ldapconn, $search_dn, $user_filter);
	    if ($sr) {
		$entry = ldap_first_entry($ldapconn, $sr);
		if ($entry) {
		    $user_dn = ldap_get_dn($ldapconn, $entry);
		    $auth_bind = ldap_bind($ldapconn, $user_dn, $_SERVER['PHP_AUTH_PW']);
		    if ($auth_bind) {			    
			$cn = Kohana::config('ldap.admin_group', FALSE);
			if ($cn) {
			    if ($this->_authorize($ldapconn, $user_dn, $cn)) {
				ldap_close($ldapconn);
				restore_error_handler();
				return TRUE;
			    }			    		
			    Kohana::log('debug', "Authorization Failed for " . $user_dn . " in group " . $cn);
			} else {
			    // No group level authorization...
			    // authentication complete
			    ldap_close($ldapconn);
			    restore_error_handler();
			    return TRUE;
			}
		    } else {
			Kohana::log('debug', "Authentication Failed for " . $user_dn);
		    }
		} else {
		    Kohana::log('debug', "No entries for user ${user_filter} in " . $search_dn);
		}
	    } else {
		Kohana::log('debug', "Unknown user ${user_filter} in " . $search_dn);
	    }
	} else {
	    Kohana::log('error', "This application is mis-configured. Unable to search LDAP using bind_dn and bind_password values from config/ldap.php");
	}
	ldap_close($ldapconn);
	restore_error_handler();
    }

    /**
     * Checks an authenticated user against a group for 
     * authorization credentials.
     * @param link_identifier $ldapconn The LDAP connection. Caller is responsible for closing and error handeling
     * @param string $user_dn
     * @param string $cn - A LDAP group
     * @return boolean - TRUE if user is authorized
     */
    private function _authorize($ldapconn, $user_dn, $cn)
    {
	// Example "(&(aking@mozilla.com,o=com,dc=mozilla)(cn=sekritCabal))"
	$filter = "(&(member=" . $user_dn . ")(${cn}))";
	$group_dn = Kohana::config('ldap.group_dn', 'ou=groups,dc=mozilla');
	$rs = ldap_list($ldapconn, $group_dn, $filter);
	if ($rs) {
	    $info = ldap_get_entries($ldapconn, $rs);
	    if ($info && $info['count'] > 0) {
		return TRUE;
	    } 
	}
	return FALSE;
    }

    /**
     * logs LDAP errors to Kohana logs. Callback suitable
     * 
     * @see set_error_handler
     * 
     * @param int $errno
     * @param string $errstr
     * @param string $errfile
     * @param int $errline
     * @param array $errcontext
     */
    private function _handle_errors($errno, $errstr, $errfile, $errline, $errcontext) {
        Kohana::log('error', "${errfile}:${errline}\terrno:${errno}\terrstr:$errstr");
        Kohana::log('error', "LDAP Error Message: " . ldap_err2str($errno));
    }
}
?>