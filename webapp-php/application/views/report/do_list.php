<?php slot::start('head') ?>
    <title>Crash Reports in <?php out::H($params['signature']) ?></title>

    <?php echo html::stylesheet(array(
        'css/flora/flora.all.css'
    ), 'screen')?>
    <!--[if IE]><?php echo html::script('js/flot-0.5/excanvas.pack.js') ?><![endif]-->

    <?php echo html::script(array(
        'js/jquery/plugins/ui/jquery.ui.all.js',
        'js/jquery/plugins/ui/jquery.tablesorter.min.js',
        'js/flot-0.5/jquery.flot.pack.js',
        'js/socorro/correlation.js',
        'js/socorro/report_list.js'
    ))?>

  <style type="text/css">
   #buildid-outer {
     display: none;
   }
   .clear {
    clear: both;
   }
  </style>    

<?php slot::end() ?>


<div class="page-heading">
	<h2><?= $correlation_os ?>
        <?php if (isset($display_signature)) { ?>
            - Crash Reports for <?php out::H($display_signature) ?>
        <?php } ?>	    
	</h2>
	<div>
	    <ul class="options">
<?php

$options = array(
	'hours' => array('6' => '6 hours', '12' => '12 hours', '24' => '24 hours', '48' => '48 hours'),
	'days' => array('3' => '3 days', '7' => '7 days', '14' => '14 days', '28' => '28 days'),
	'weeks' => array('1' => '1 week', '2' => '2 weeks', '3' => '3 weeks', '4' => '4 weeks'),
);

$type = $params['range_unit'];
$current = $params['range_value'];
$urlParams = $params;

foreach($options[$type] as $k => $readable) {
	$urlParams['range_value'] = $k;
	echo '<li><a href="' . url::site('report/list') . '?' . html::query_string($urlParams) . '"';
	if ($k == $params['range_value']) {
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

<p>
<?php 
    View::factory('common/prose_params', array(
        'params'    => $params,
        'platforms' => $all_platforms
    ))->render(TRUE) 
?>
</p>
<?php if(count($reports) > 0): ?> 
<div id="report-list">
    <ul id="report-list-nav">
        <li><a href="#graph"><span>Graph</span></a></li>
        <li><a href="#table"><span>Table</span></a></li>
        <li><a href="#reports"><span>Reports</span></a></li>
<?php if (array_key_exists($params['signature'], $sig2bugs)) { ?>    
							       <li><a href="#bugzilla"><span>Bugzilla (<?= count($sig2bugs[$params['signature']])?>)</span></a></li>
<?php } ?>
	<li><a href="#comments"><span>Comments (<?= count($comments) ?>)</span></a></li>
        <li><a href="#correlation"><span>Correlations</span></a></li>
    </ul>
    <div id="graph">
      <div class="crashes-by-platform">
        <h3 id="by_platform_graph"><?php echo $crashGraphLabel ?></h3>
        <div id="graph-legend" class="crash-plot-label"></div>
        <div id="buildid-graph"></div>
      </div>
      <div class="clear"></div>
    </div>
    <div id="table">
        <table id="buildid-table" class="tablesorter">
            <thead>
                <tr>
                    <th>Build ID</th>
                    <?php if (count($all_platforms) != 1): ?><th>Crashes</th><?php endif ?>
                    <?php foreach ($all_platforms as $platform): ?>
                        <th><?php out::H(substr($platform->name, 0, 3)) ?></th>
                    <?php endforeach ?>
                </tr>
            </thead>
            <tbody>
                <?php foreach ($builds as $build): ?>
                <tr>
	   <td class="human-buildid"><?php out::H(date('YmdH', strtotime($build->build_date))) ?></td>
                    <?php if (count($all_platforms) != 1): ?>
                    <td class="crash-count">
		    <?php out::H($build->count) ?> - <?php printf("%.3f%%", ($build->frequency * 100) ) ?>
                    </td>
                    <?php endif ?>
                    <?php foreach ($all_platforms as $platform): ?>
                        <td>
                            <?php out::H($build->{"count_$platform->id"}) ?> - 
                            <?php printf("%.3f%%", ($build->{"frequency_$platform->id"} * 100)) ?>
                        </td>
                    <?php endforeach ?>
                </tr>
                <?php endforeach ?>
            </tbody>
        </table>
    </div>

    <div id="reports">
	<?php View::factory('moz_pagination/nav')->render(TRUE); ?>
        <?php View::factory('common/list_reports', array(
            'reports' => $reports 
        ))->render(TRUE) ?>
	<?php View::factory('moz_pagination/nav')->render(TRUE); ?>
        <br />
    </div>

<?php if (array_key_exists($params['signature'], $sig2bugs)) { ?>    
    <div id="bugzilla">      
        <?php View::factory('common/list_bugs', array(
		     'signature' => $params['signature'],
                     'bugs' => $sig2bugs[$params['signature']],
                     'mode' => 'full'
	      ))->render(TRUE); ?>
       <?php if (count($sig2bugs) > 1) { ?>
	    <h2>Related Crash Signatures:</h2>
       <?php
	        foreach ($sig2bugs as $sig => $bugs) {
	            if ($sig != $params['signature']) {
                        View::factory('common/list_bugs', array(
		            'signature' => $sig,
                            'bugs' => $bugs,
                            'mode' => 'full'
	      ))->render(TRUE);
	            }
	        }
	     } ?>
        <br class="cb" />
    </div>

<?php } 
    View::factory('common/comments')->render(TRUE);
    View::factory('common/correlation', array(
		      'current_signature' => $params['signature'],
		      'current_product' => $correlation_product,
		      'current_version' => $correlation_version,
		      'current_os' => $correlation_os))->render(TRUE);
?>


        </div>
	<?php else: ?>
	<p>There were no reports in the time period specified. Please choose a different time period or use advanced search to select a custom time period.</p>
	<?php endif; ?>
    </div>
</div>


<!-- end content -->
<script id="source" type="text/javascript">
//<![CDATA[
      $(document).ready(function() { 
          var shouldDrawPlot = true;
	  <?php if( count($builds) > 1){ ?>
	    $("#buildid-graph").width(<?php echo max( min(50 * count($builds), 800), 200) ?>);
	  <? } ?>

      $('#report-list > ul').bind('tabsshow', function(event, ui, data){
	  if (shouldDrawPlot && $(data.panel).attr('id') == "graph") {
            drawPlot();
            shouldDrawPlot = false;
        }
    });

    var drawPlot = function(){
      $.plot($("#buildid-graph"), 
             [<?php for($i = 0; $i < count($all_platforms); $i += 1){ 
		      $platform = $all_platforms[$i]; ?>
			{ label: <?php echo json_encode($platformLabels[$i]['label']) ?>,
		          data: <?php  echo json_encode($platformLabels[$i]['data']) ?>,
			  color: <?php echo json_encode($platformLabels[$i]['color']); 
			  if($i != (count($all_platforms) -1 )){ echo '},';}else{ echo '}';} ?>
	       <?php } ?> ],
             { // options

             <?php if( count($builds) > 1){ ?>
	       // Crashes by development builds Frequency over build day
               lines: { show: true }, points: { show: true},
	       xaxis:{
                 labelWidth: 55,
 	         ticks: <?php echo json_encode( $buildTicks ) ?>
	       },
	       legend: { show: true, container: $("#graph-legend"), noColumns: 4 }

	     <?php }else{ ?>
	       //Crashes for production build OS bar chart
               bars: { show: true },
               xaxis:{
                 labelWidth: 55,
   	         tickFormatter: function(n, o){ return ""; }
	       },
	       legend: { show: true, container: $("#graph-legend"), noColumns: 4 }
	     <?php } ?>		 
             }
     );
    }//drawPlot

});
//]]>
</script>
