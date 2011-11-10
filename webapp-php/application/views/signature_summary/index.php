<?php slot::start('head') ?>
    <title>Signature Summary for <?php out::H($signature) ?></title>

    <?php echo html::stylesheet(array(
        'css/flora/flora.all.css',
        'css/signature_summary.css',
    ), 'screen')?>
    <!--[if IE]><?php echo html::script('js/flot-0.7/excanvas.pack.js') ?><![endif]-->

    <script type="text/javascript">
        var json_path = "<?= $data_url ?>"
    </script>

    <?php echo html::script(array(
        'js/jquery/mustache.js',
        'js/socorro/signature_summary.js',
        'js/socorro/socorro.dashboard.js'
    ))?>

<?php slot::end() ?>


<div class="page-heading">
	<h2>Signature Summary for <?= $signature ?>	</h2>
	<div>
	    <ul class="options">
<?php

$options =	array('3' => '3 days', '7' => '7 days', '14' => '14 days', '28' => '28 days');

$current = $duration;

foreach($options as $k => $readable) {
	$urlParams['duration'] = $k;
    $urlParams['signature'] = $signature;
	echo '<li><a href="' . url::site('signature_summary') . '?' . html::query_string($urlParams) . '"';
	if ($k == $duration) {
	    echo ' class="selected"';
	}
	echo ">" . $readable . '</a></li>';
}

?>
            </ul>
	</div>

</div>

<div class="panel">
    <div class="body notitle">

	<div class="sig-dashboard-body">
		<table id="pbos" class="sig-dashboard-tbl zebra">
			<thead>
				<tr>
					<th>Operating System</th>
					<th>Percentage</th>
					<th>Number Of Crashes</th>
				</tr>
			</thead>
			<tbody id="percentageByOsBody">
				
			</tbody>
		</table>
		
		<table id="rou" class="sig-dashboard-tbl zebra">
			<thead>
				<tr>
					<th>Uptime Range</th>
					<th>Percentage</th>
					<th>Number Of Crashes</th>
				</tr>
			</thead>
			<tbody id="uptimeRangeBody">
				
			</tbody>
		</table>
		
		<table class="sig-dashboard-tbl zebra">
			<thead>
				<tr>
					<th>Product</th>
					<th>Version</th>
					<th>Percentage</th>
					<th>Number Of Crashes</th>
				</tr>
			</thead>
			<tbody id="productVersionsBody">
				
			</tbody>
		</table>
	</div>

    </div>
</div>
