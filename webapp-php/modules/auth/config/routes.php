/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<?php defined('SYSPATH') OR die('No direct access allowed.');
/**
 * @package  Auth
 *
 * Sets the custom routes for the Auth module.
 */


/**
 * Set up the root routes.
 */
$config['email'] 	= 'auth/email';
$config['forgot'] 	= 'auth/forgot';
$config['login'] 	= 'auth/login';
$config['logout'] 	= 'auth/logout';
$config['password'] = 'auth/password';
$config['register'] = 'auth/register';
$config['verify'] 	= 'auth/verify';
