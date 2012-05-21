/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<?php defined('SYSPATH') or die('No direct script access.');
/**
 * @package  Cache:SQLite
 */
$config['schema'] =
'CREATE TABLE caches(
	id varchar(127) PRIMARY KEY,
	hash char(40) NOT NULL,
	tags varchar(255),
	expiration int,
	cache blob);';
