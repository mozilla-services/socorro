<?php defined('SYSPATH') or die('No direct script access.');

$config['topcrashbysig_numberofsignatures'] = 3;
$config['topcrashbysig_featured'] = array(
    array('product' => 'Firefox',         'version' => '3.5b4pre'),
    array('product' => 'Thunderbird', 'version' => '3.0b3pre'),
    array('product' => 'SeaMonkey',  'version' => '2.0a3pre'),
    array('product' => 'Sunbird',        'version' => '1.0pre'),
    array('product' => 'Camino',        'version' => '2.0b3pre')
);
$config['topcrashbyurl_numberofurls'] = 3;
$config['topcrashbyurl_featured'] = array(
    array('product' => 'Firefox',         'version' => '3.1b2')
);
$config['mtbf_featured'] = array(
    array('product' => 'Firefox',     'release' => 'development'),
    array('product' => 'Thunderbird', 'release' => 'development'));

?>