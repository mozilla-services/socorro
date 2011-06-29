
<?php slot::start('head') ?>
    <title>Crash Data for Mozilla <?php out::H($product) ?> <?php out::H($version); ?></title>
<?php slot::end() ?>


<?php slot::start('head') ?>
    <title>Crash Data for Mozilla <?php out::H($product) ?>
        <?php if (isset($version) && !empty($version)) { ?>
            <?php out::H($version); ?>
        <?php } ?>
    </title>
<?php slot::end() ?>


<?php
echo html::stylesheet(array(
		'css/daily.css',				
	), array('screen', 'screen'));
echo '<script>var data = ' . json_encode($graph_data) . '</script>';
echo html::script(array(
		'js/flot-0.7/jquery.flot.pack.js',
		'js/socorro/daily.js',
		'js/socorro/topcrashers.js'
	));

View::factory('common/dashboard_product', array(
    'duration' => $duration,
    'graph_data' => $graph_data,
    'product' => $product,
    'top_crashers' => $top_crashers,
    'url_base' => $url_base,
    'version' => $version,
))->render(TRUE);

?>
