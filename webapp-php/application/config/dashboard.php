<?php defined('SYSPATH') or die('No direct script access.');
$config['default_product'] = "Thunderbird";//"Firefox";
$config['topcrashbysig_numberofsignatures'] = 3;
$config['topcrashbysig_featured'] = array(
    array('product' => 'Firefox',         'version' => '3.6a1pre'),
    array('product' => 'Thunderbird', 'version' => '3.0b4pre'),
    array('product' => 'SeaMonkey',  'version' => '2.0a3pre'),
    array('product' => 'Sunbird',        'version' => '1.0pre'),
    array('product' => 'Camino',        'version' => '2.0b4pre')
);
$config['topcrashbyurl_numberofurls'] = 3;
$config['topcrashbyurl_featured'] = array(
    array('product' => 'Firefox',         'version' => '3.0b4pre')
);
$config['mtbf_featured'] = array(
    array('product' => 'Firefox',     'release' => 'development'),
    array('product' => 'Thunderbird', 'release' => 'development'));

?>