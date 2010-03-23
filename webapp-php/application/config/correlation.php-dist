<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Base path to Correlation reports. Should end in a '/'.
 */
$config['path'] = 'http://people.mozilla.com/crash_analysis/';

/**
 * The maximum file size in megabytes we should read per platform.
 * -1 for no limit.
 * Example: 2 - Load 2MB of data from each platform section of a correlation
 * report.
 */
$config['max_file_size'] = 2;

/**
 * Cache config, much like webapp-php/application/config/cache.php
 * but only affects the caching mechanism for loading correlatin 
 * reports off of people.mozilla.com.
 *
 * Any cache parameters not set will be inheritied from cache.php
 */
$config['caching'] = array('lifetime' => (60 * 60 * 14)); //in Seconds, so 14 hours

/**
 * It can take a looooong time to go grab the files off people
 * parse them, and format a response.
 * This controls overriding the php timeout to allow for long running ajax requests.
 */
$config['file_processing_timeout'] = 60 * 5; // 5 minutes
?>