/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<?php defined('SYSPATH') or die('No direct script access.');
/**
 * @package  Encrypt
 *
 * Encrypt configuration is defined in groups which allows you to easily switch
 * between different encryption settings for different uses.
 * Note: all groups inherit and overwrite the default group.
 *
 * Group Options:
 *  key    - Encryption key used to do encryption and decryption. The default option
 *           should never be used for a production website.
 *
 *           For best security, your encryption key should be at least 16 characters
 *           long and contain letters, numbers, and symbols.
 *           @note Do not use a hash as your key. This significantly lowers encryption entropy.
 *
 *  mode   - MCrypt encryption mode. By default, MCRYPT_MODE_NOFB is used. This mode
 *           offers initialization vector support, is suited to short strings, and
 *           produces the shortest encrypted output.
 *           @see http://php.net/mcrypt
 *
 *  cipher - MCrypt encryption cipher. By default, the MCRYPT_RIJNDAEL_128 cipher is used.
 *           This is also known as 128-bit AES.
 *           @see http://php.net/mcrypt
 */
$config['default'] = array
(
	'key'    => 'K0H@NA+PHP_7hE-SW!FtFraM3w0R|<',
	'mode'   => MCRYPT_MODE_NOFB,
	'cipher' => MCRYPT_RIJNDAEL_128
);
