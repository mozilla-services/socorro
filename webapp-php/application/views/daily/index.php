<?php slot::start('head') ?>
    <title>Crashes per Active Daily User for <?php out::H($product) ?></title>
    <link title="CSV formatted Crashes per Active Daily User for <?php out::H($product) ?>" type="text/csv" rel="alternate" href="<?php out::H($url_csv); ?>" />

<?php
echo html::stylesheet(array(
		'css/daily.css',				
	), array('screen', 'screen'));
?>
<?php slot::end() ?>

<?php
echo '<script>var data = ' . json_encode($graph_data) . '</script>';
echo html::script(array(
		'js/flot-0.5/jquery.flot.pack.js',
		'js/socorro/daily.js',
	));
?>

<div class="page-heading">
	<h2>Crashes per Active Daily User</h2>
</div>

<?php
    View::factory('daily/daily_search', array(
        'date_start' => $date_start,
        'date_end' => $date_end,
        'duration' => $duration,
        'form_selection' => $form_selection,
		'graph_data' => $graph_data,
        'operating_system' => $operating_system,
        'operating_systems' => $operating_systems,    		
        'product' => $product,                       	
        'products' => $products,                      		
        'url_form' => $url_form,
        'versions' => $versions
	))->render(TRUE);
?>

<div class="panel daily_graph">
	<div class="title">
		<h2>Crashes per 1k ADU</h2>
    </div>

    <div class="body">
        <?php if (!empty($graph_data)) { ?>
		    <div id="sig-history-graph"></div>
		<?php } else { ?>
		    <p>No crash data is available for this report.</p>
		<?php } ?>

        <br class="clear">
	</div>
</div>

<br class="clear" />

<?php
    if (!empty($graph_data)) { 
        View::factory($file_crash_data, array(
            'dates' => $dates,
            'operating_systems' => $operating_systems,
            'results' => $results,
            'statistics' => $statistics,
	    	'url_csv' => $url_csv,
            'versions' => $versions
	    ))->render(TRUE);
    }
?>
