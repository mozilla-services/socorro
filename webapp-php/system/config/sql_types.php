/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<?php defined('SYSPATH') or die('No direct script access.');
/**
 * @package  Database
 *
 * SQL data types. If there are missing values, please report them:
 *
 * @link  http://trac.kohanaphp.com/newticket
 */
$config = array
(
	'tinyint'      => array('type' => 'int', 'max' => 127),
	'smallint'     => array('type' => 'int', 'max' => 32767),
	'mediumint'    => array('type' => 'int', 'max' => 8388607),
	'int'          => array('type' => 'int', 'max' => 2147483647),
	'integer'      => array('type' => 'int', 'max' => 2147483647),
	'bigint'       => array('type' => 'int', 'max' => 9223372036854775807),
	'float'        => array('type' => 'float'),
	'boolean'      => array('type' => 'boolean'),
	'time'         => array('type' => 'string', 'format' => '00:00:00'),
	'date'         => array('type' => 'string', 'format' => '0000-00-00'),
	'year'         => array('type' => 'string', 'format' => '0000'),
	'datetime'     => array('type' => 'string', 'format' => '0000-00-00 00:00:00'),
	'char'         => array('type' => 'string', 'exact' => TRUE),
	'binary'       => array('type' => 'string', 'binary' => TRUE, 'exact' => TRUE),
	'varchar'      => array('type' => 'string'),
	'varbinary'    => array('type' => 'string', 'binary' => TRUE),
	'blob'         => array('type' => 'string', 'binary' => TRUE),
	'text'         => array('type' => 'string')
);

// DOUBLE
$config['double'] = $config['decimal'] = $config['real'] = $config['numeric'] = $config['float'];

// BIT
$config['bit'] = $config['boolean'];

// TIMESTAMP
$config['timestamp'] = $config['datetime'];

// ENUM
$config['enum'] = $config['set'] = $config['varchar'];

// TEXT
$config['tinytext'] = $config['mediumtext'] = $config['longtext'] = $config['text'];

// BLOB
$config['tinyblob'] = $config['mediumblob'] = $config['longblob'] = $config['clob'] = $config['blob'];
