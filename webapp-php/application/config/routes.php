<?php defined('SYSPATH') or die('No direct access allowed.');
/**
 * @package  Core
 *
 * Sets the default route to "welcome"
 */
# $config['_default'] = 'welcome';

$config['_default'] = 
    'home/dashboard';

$config['query'] =
    'query/query';

$config['status'] = 
    'status/index';

$config['topcrasher/byversion/([a-zA-Z.]+)/([0-9a-zA-Z.]+)/([0-9]+)'] =
    'topcrasher/byversion/$1/$2/$3';

$config['topcrasher/byversion/([a-zA-Z.]+)/([0-9a-zA-Z.]+)'] =
    'topcrasher/byversion/$1/$2';

$config['topcrasher/bybranch/([0-9a-zA-Z.]+)'] =
    'topcrasher/bybranch/$1';

$config['topcrasher'] =
    'topcrasher/index';

$config['error/(.*)/(.*)'] =
    'error/$1/$2';

$config['dumps/(.*)'] =
    'dumps/file/$1';

$config['report/list'] =
    'report/do_list'; // 'list' is a PHP reserved word

$config['report/find'] =
    'report/find';

$config['report/index/([0-9a-zA-Z.]+)'] =
    'report/index/$1';
