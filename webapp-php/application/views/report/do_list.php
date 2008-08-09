<?php slot::start('head') ?>
    <title>Crash Reports in <?php out::H($params['signature']) ?></title>

    <?php echo html::stylesheet(array(
        'css/flora/flora.all.css'
    ), 'screen')?>

    <?php echo html::script(array(
        'js/MochiKit/MochiKit.js',
        'js/PlotKit/excanvas.js',
        'js/PlotKit/PlotKit_Packed.js',
        'js/jquery/jquery-1.2.1.js',
        'js/jquery/plugins/ui/ui.tabs.js',
        'js/jquery/plugins/ui/jquery.tablesorter.min.js'
    ))?>

  <script type="text/javascript">
      $(document).ready(function() { 
        $('#buildid-table').tablesorter(); 
        $('#reportsList').tablesorter({sortList:[[8,1]]});
        $('#report-list > ul').tabs();
      }); 
  </script>

  <style type="text/css">
   #buildid-outer {
     display: none;
   }
   #buildid-div {
     float: left;
     height: 160px;
     width: 500px;
     margin-top: 0.5em;
     margin-bottom: 0.5em;
     margin-left: auto;
     margin-right: 1.5em;
   }
   #buildid-labels {
   }
   .clear {
    clear: both;
   }
  </style>    

    <?php echo html::stylesheet(array(
        'css/layout.css',
        'css/style.css'
    ), 'screen')?>

<?php slot::end() ?>

<h1 class="first">Crash Reports in <?php out::H($params['signature']) ?></h1>

<?php 
    View::factory('common/prose_params', array(
        'params'    => $params,
        'platforms' => $all_platforms
    ))->render(TRUE) 
?>

<div id="report-list">
    <ul>
        <li><a href="#graph"><span>Graph</span></a></li>
        <li><a href="#table"><span>Table</span></a></li>
        <li><a href="#reports"><span>Reports</span></a></li>
    </ul>
    <div id="graph">
        <div id="buildid-outer"> <div id="buildid-div"> <canvas id="buildid-graph" width="500" height="160"></canvas>
            </div>
            <ul id="buildid-labels">
                <?php foreach ($all_platforms as $platform): ?>
                    <li style="color: <?php echo $platform->color ?>"><?php out::H($platform->name) ?></li>
                <?php endforeach ?>
            </ul>
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
                    <td class="crash-count" py:if="len(c.params.platforms) != 1">
                        <?php out::H($build->count) ?> - <?php printf("%.3f%%", ($build->frequency * 100)) ?>
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
        <?php View::factory('common/list_reports', array(
            'reports' => $reports 
        ))->render(TRUE) ?>
    </div>
</div>

<!-- end content -->

 <script type="text/javascript">

 var data = [
  <?php foreach ($builds as $build): ?>
    <?php if ($build->total <= 10) continue ?>
    [ <?php echo strtotime($build->build_date) ?> * 1000 , <?php out::H($build->total) ?>,
    <?php foreach ($all_platforms as $platform): ?>
        <?php out::H($build->{"frequency_$platform->id"}) ?> , 
    <?php endforeach ?>
   ],
  <?php endforeach ?>
  null
 ];
 data.pop();

 var total_platforms = <?php echo count($all_platforms) ?>;

 var minDate = 1e+14;
 var maxDate = 0;
 var maxValue = 0;

 var platformData = [];
 for (var p = 0; p < total_platforms; ++p)
   platformData[p] = [];

 for (var i = 0; i < data.length; ++i) {
   var date = data[i][0];
   if (date > maxDate)
     maxDate = date;
   if (date < minDate)
     minDate = date;

   var value = 0;
   for (p = total_platforms - 1; p >= 0; --p) {
     value += data[i][p + 2]
     platformData[p][i] = [date, value];
   }
   if (value > maxValue)
     maxValue = value;
 }

 function pad2(n)
 {
   return ("0" + n.toString()).slice(-2);
 };

 function formatDate(d)
 {
   return pad2(d.getUTCMonth() + 1) + "-" + pad2(d.getUTCDate());
 }

 var interval = (maxDate - minDate) / 8;

 var xTicks = [];
 for (var i = 0; i <= 8; ++i) {
   var e = minDate + interval * i;
   var d = new Date(e);
   d.setUTCHours(0);
   d.setUTCMinutes(0);

   xTicks.push({label: formatDate(d), v: d.getTime()});
 }

 function formatPercent(v)
 {
   return (v * 100).toFixed(1) + "%";
 }

 var yTicks = [];
 interval = maxValue / 5;

 for (var i = 0; i <= 5; ++i) {
   e = interval * i;
   yTicks.push({label: formatPercent(e), v: e});
 }

 var layout = new Layout("line", {xOriginIsZero: false,
                                  xTicks: xTicks,
				  yTicks: yTicks});

 for(p = 0; p < total_platforms; ++p) {
   layout.addDataset("total_" + p, platformData[p]);
 }

 layout.evaluate();

 if (maxValue > 0) {
   var colors = [
    <?php foreach ($all_platforms as $platform): ?>
         Color.fromHexString('<?php echo $platform->color ?>'),
    <?php endforeach ?>
     null
   ]; 
   colors.pop();

   var chart = new CanvasRenderer(MochiKit.DOM.getElement('buildid-graph'), layout,
         {IECanvasHTC: '<?php echo url::base().'js/PlotKit/iecanvas.htc' ?>',
		 colorScheme: colors,
		 shouldStroke: true,
		 strokeColor: null,
		 strokeWidth: 2,
     shouldFill: false,
     axisLabelWidth: 75});

     chart.render();

     MochiKit.DOM.getElement('buildid-outer').style.display = 'block';
 }
 </script>
