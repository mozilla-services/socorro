<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<?php slot::start('head') ?>
    <title>Crash Reports in <?php out::H($params['signature']) ?></title>

    <?php echo html::stylesheet(array(
        'css/flora/flora.all.css',
        'css/signature_summary.css'
    ), 'screen')?>
    <!--[if IE]><?php echo html::script('js/flot-0.7/excanvas.pack.js') ?><![endif]-->
    <?php
        $sigParams = array('range_value' => $params['range_value'], 'range_unit' => $params['range_unit'], 'signature' => $params['signature'], 'version' => $params['version']);
        if(isset($params['date']) && !empty($params['date'])) {
            $sigParams['date'] = $params['date'];
        }
        $data_url = url::site('signature_summary/json_data') . '?' . html::query_string($sigParams)
    ?>

    <script type="text/javascript">
        var json_path = "<?= $data_url ?>";
    </script>

    <?php echo html::script(array(
        'js/jquery/plugins/ui/jquery-ui-1.8.16.tabs.min.js',
        'js/jquery/plugins/jquery.cookie.js',
        'js/jquery/plugins/ui/jquery.tablesorter.min.js',
        'js/flot-0.7/jquery.flot.pack.js',
        'js/socorro/correlation.js',
        'js/socorro/report_list.js',
        'js/socorro/bugzilla.js',
        'js/jquery/mustache.js',
        'js/socorro/signature_summary.js',
        'js/socorro/socorro.dashboard.js'
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
        <h2>
            <?php if (isset($display_signature)) { ?>
                Crash Reports for <?php out::H($display_signature) ?>
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
        <li><a href="#sigsummary"><span>Signature Summary</span></a></li>
        <li><a href="#graph"><span>Graph</span></a></li>
        <li><a href="#table"><span>Table</span></a></li>
        <li><a href="#reports"><span>Reports</span></a></li>
<?php if (array_key_exists($params['signature'], $sig2bugs)) { ?>
	<li><a href="#bugzilla"><span>Bugzilla (<?= count($sig2bugs[$params['signature']])?>)</span></a></li>
<?php } ?>
	<li><a href="#comments"><span>Comments (<?= count($comments) ?>)</span></a></li>
        <li><a href="#correlation"><span>Correlations</span></a></li>
        <?php if ($logged_in) { ?>
            <li><a href="#sigurls"><span>URLs</span></a></li>
        <?php } ?>
    </ul>

    <div id="sigsummary">
        <?php View::factory('signature_summary/index', array('range_unit' => $type, 'range_value' => $current, 'signature' => $params['signature']))->render(TRUE) ?>
    </div>

    <div id="graph">
      <div class="crashes-by-platform">
        <h3 id="by_platform_graph"><?php echo $crashGraphLabel ?></h3>
        <div id="graph-legend" class="crash-plot-label"></div>
        <div id="buildid-graph"></div>
      </div>
	  <h3>Hover over a point above the see the crash build date.</h3>
      <div class="clear"></div>
    </div>
    <div id="table">
        <table id="buildid-table" class="tablesorter data-table">
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
	   <td class="human-buildid"><?php out::H(gmdate('YmdH', strtotime($build->build_date))) ?></td>
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
    if ($logged_in) {
        View::factory('common/signature_urls', array(
            'urls' => $urls,
            'display_signature' => $display_signature
        ))->render(TRUE);
    }
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
          var shouldDrawPlot = true,
          currentActiveTab = $("#report-list-nav").find("li.ui-tabs-selected");
	  <?php if( count($builds) > 1){ ?>

	    $("#buildid-graph").width(<?php echo max( min(300 * count($builds), 1200), 200) ?>);
	  <? } ?>

      var drawPlot = function() {

      var buildIdGraph = $.plot($("#buildid-graph"),
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
            lines: {
				show: true
			},
			points: {
				show: true
			},
	        xaxis: {
                labelWidth: 55,
				ticks: <?php echo json_encode( $buildTicks ) ?>
	        },
            yaxis: {
                min: 0,
            },
		    grid: { hoverable: true },
	        legend: {
				show: true,
				container: $("#graph-legend"),
				noColumns: 4
			}

	     <?php }else{ ?>
	       //Crashes for production build OS bar chart
               bars: { show: true },
               xaxis:{
                 labelWidth: 55,
   	         tickFormatter: function(n, o){ return ""; }
	       },
            yaxis: {
                min: 0,
            },
	       legend: { show: true, container: $("#graph-legend"), noColumns: 4 }
	     <?php } ?>
             }
     );

		/* Hiding dates if they exceed a number > 20 to avoid overlap */
		if(buildIdGraph.getAxes().xaxis.ticks.length > 20) {
			$(".xAxis").hide();
		}

    }//drawPlot

    // If the last selected tab was the graph, we need to ensure that the graph
    // is plotted on document ready.
    if(shouldDrawPlot && currentActiveTab.find("a").attr("href") === "#graph") {
        drawPlot();
        shouldDrawPlot = false;
    }

    // if the last selected tab was not the graph, we need to ensure the graph
    // is plotted once the graph tab is clicked.
    $('#report-list').bind('tabsselect, tabsshow', function(event, ui) {
        if (shouldDrawPlot && $(ui.panel).attr('id') == "graph") {
            drawPlot();
            shouldDrawPlot = false;
        }
    });

	function showTooltip(x, y, contents) {
		$('<div id="graph-tooltip">' + contents + '</div>').css({
			top: y + 5,
			left: x + 5
		}).appendTo("body").fadeIn(200);
	}

	var previousPoint = null;

	$("#buildid-graph").bind("plothover", function (event, pos, item) {
		$("#x").text(pos.x.toFixed(2));
		$("#y").text(pos.y.toFixed(2));

		if (item) {

			if (previousPoint != item.dataIndex) {

				previousPoint = item.dataIndex;

				$("#graph-tooltip").remove();

				var x = item.datapoint[0].toFixed(2),
				y = item.datapoint[1].toFixed(2);

				showTooltip(item.pageX, item.pageY, "Crash build date: " + item.series.xaxis.ticks[previousPoint].label);
			}
		} else {
			$("#graph-tooltip").remove();
			previousPoint = null;
		}
	});
});
//]]>
</script>
