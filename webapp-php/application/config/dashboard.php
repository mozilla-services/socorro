<?php defined('SYSPATH') or die('No direct script access.');
$config['default_product'] = "
Firefox";
$config['topcrashbysig_numberofsignatures'] = 3;
$config['topcrashbysig_featured'] = array(
    array('product' => 'Firefox',     'version' => '3.6a2pre'),
    array('product' => 'Thunderbird', 'version' => '3.0b3'),
    array('product' => 'SeaMonkey',   'version' => '2.1a1pre')
);
$config['topcrashbyurl_numberofurls'] = 3;
$config['topcrashbyurl_featured'] = array(
    array('product' => 'Firefox',     'version' => '3.5.3'),
    array('product' => 'Camino',      'version' => '2.0b4'),
    array('product' => 'SeaMonkey',   'version' => '2.1a1pre')
);
$config['mtbf_featured'] = array(
    array('product' => 'Firefox',     'release' => 'development'),
    array('product' => 'Thunderbird', 'release' => 'development'));

?>