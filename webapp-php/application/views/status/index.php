<?php slot::start('head') ?>
    <title>Server Status</title>
    <?php echo html::stylesheet(array(
       'css/flora/flora.all.css'
    ), 'screen')?>
    <!--[if IE]><?php echo html::script('js/flot-0.5/excanvas.pack.js') ?><![endif]-->
    <?php echo html::script(array(
        'js/jquery/plugins/ui/jquery.tablesorter.min.js',
        'js/flot-0.5/jquery.flot.pack.js'
    ))?>
<?php slot::end() ?>

<h1 class="first">Server Status</h1>
<?php $stat = $server_stats[0] ?>

<div id="at-a-glance">
<h2>At a Glance</h2>
<dl>
  <dt>Mood</dt>
  <dd><span class="server-status <?php echo $status ?>"><?php echo ucwords($status); ?></span></dd>
  <dt>Server Time</dt>
  <dd><?= date('Y-m-d H:i:s', time()) ?></dd>
  <dt>Stats Created At</dt>
  <dd><?php echo $stat->date_created ?></dd>
  <dt>Waiting Jobs</dt>
  <dd><?php echo $stat->waiting_job_count ?></dd>
  <dt>Processors Running</dt>
  <dd><?php echo $stat->processors_count ?></dd>
  <dt>Average Seconds to Process</dt>
  <dd><?php echo $stat->avg_process_sec ?></dd>
  <dt>Average Wait in Seconds</dt>
  <dd><?php echo $stat->avg_wait_sec ?></dd>
  <dt>Recently Completed</dt>
  <dd><?php echo $stat->date_recently_completed ?></dd>
  <dt>Oldest Job In Queue</dt>
  <dd><?php echo $stat->date_oldest_job_queued ?></dd>
</dl>
</div>

<div id="graphs" class="hidden">
  <h2>Graphs</h2>
  <div id="graph-chooser-container">
  <label for="graph-chooser">Choose a graph:</label>
  <select id="graph-chooser">
  <option value="server-status-comb">Combined server status</option>
  <option value="server-status-jobs-wait">Total number of jobs waiting</option>
  <option value="server-status-proc-count">Total number of processors</option>
  <option value="server-status-avg-proc">Average time to process a job</option>
  <option value="server-status-avg-wait">Average time a job waits</option>
  </select>
  </div>
  
  <div id="server-status-comb">
    <h3>Combined server status</h3>
    <div id="server-status-graph-comb"></div>
    <div class="caption server-plot-label">Combined server status in 5 minute intervals. Measurements on left are for counts and the measurements on the right are in seconds</div>
  </div>
  
  <div id="server-status-jobs-wait">
    <h3>Total number of jobs waiting</h3>
    <div id="server-status-graph-jobs-wait"></div>
  </div>
  
  <div id="server-status-proc-count">
    <h3>Total number of processors</h3>
    <div id="server-status-graph-proc-count"></div>
  </div>
  
  <div id="server-status-avg-proc">
    <h3>Average time to process a job</h3>
    <div id="server-status-graph-avg-proc"></div>
  </div>
  
  <div id="server-status-avg-wait">
    <h3>Average time a job waits</h3>
    <div id="server-status-graph-avg-wait"></div>
  </div>
</div>

<h3 id="server-stats">Latest Raw Stats</h3>
<table id="server-stats-table" class="tablesorter">
  <thead>
    <tr>
      <th class="header">Time</th>
      <th class="header">Waiting Jobs</th>
      <th class="header">Processors</th>
      <th class="header">Average Seconds to Process</th>
      <th class="header">Average Wait in Seconds</th>
      <th class="header">Recently Completed</th>
      <th class="header">Oldest Job In Queue</th>
    </tr>
  </thead>
  <tbody>
    <?php foreach ($server_stats as $stat): ?>
    <tr id="server_stats_row-<?php echo $stat->id; ?>">
      <td><?php echo $stat->date_created; ?></td>
      <td><?php echo $stat->waiting_job_count; ?></td>
      <td><?php echo $stat->processors_count; ?></td>
      <td><?php echo $stat->avg_process_sec; ?></td>
      <td><?php echo $stat->avg_wait_sec; ?></td>
      <td><?php echo $stat->date_recently_completed; ?></td>
      <td><?php echo $stat->date_oldest_job_queued; ?></td>
    </tr>
  <?php endforeach ?>
  </tbody>
</table>

<script id="source" type="text/javascript">
$('#graphs').removeClass('hidden');
$(function(){
  var waiting_job_count = <?php echo json_encode($plotData['waiting_job_count']);?>;
  var processors_count = <?php echo json_encode($plotData['processors_count']);?>;
  var avg_process_sec = <?php echo json_encode($plotData['avg_process_sec']); ?>;
  var avg_wait_sec = <?php echo json_encode($plotData['avg_wait_sec']); ?>;

  $.plot($("#server-status-graph-comb"),
   [
          {label:"Jobs Waiting", data: waiting_job_count },
          {label:"Proc Running", data: processors_count},
          {label:"Avg Process", yaxis: 2, data: avg_process_sec},
          {label:"Avg Wait", yaxis: 2, data: avg_wait_sec}
         ],
         { // options 
   xaxis: {
     ticks: <?php echo json_encode( $plotData['xaxis_ticks'] ); ?>
     }, yaxis: { labelWidth: 55 }
  });
  $.plot($("#server-status-graph-jobs-wait"),
   [ {label:"Jobs Waiting", data: waiting_job_count }],
         { // options 
   xaxis: {
     ticks: <?php echo json_encode( $plotData['xaxis_ticks'] ); ?>
       }, yaxis: { labelWidth: 55 }
  });

  $.plot($("#server-status-graph-proc-count"),
   [ {label:"Proc Running", data: processors_count} ],
         { // options 
   xaxis: {
     ticks: <?php echo json_encode( $plotData['xaxis_ticks'] ); ?>
     }, yaxis: { labelWidth: 55 }
  });

  $.plot($("#server-status-graph-avg-proc"),
   [ {label:"Avg Process", data: avg_process_sec} ],
         { // options 
   xaxis: {
     ticks: <?php echo json_encode( $plotData['xaxis_ticks'] ); ?>
     }, yaxis: { labelWidth: 55 }
  });

  $.plot($("#server-status-graph-avg-wait"),
   [ {label:"Avg Wait", data: avg_wait_sec} ],
         { 
   xaxis: {
     ticks: <?php echo json_encode( $plotData['xaxis_ticks'] ); ?>
     }, yaxis: { labelWidth: 55 }
  });
});

$(document).ready(function() { 
  $('#server-stats-table').tablesorter(); 
  $('#graph-chooser').change(showGraph);
  hideAllGraphs();  
  $('#server-status-comb').show();
}); 

function showGraph() {
  var selected = $('#graph-chooser').val();
  hideAllGraphs();  
  $('#' + selected).show();
}

function hideAllGraphs() {
  $('#server-status-comb').hide();
  $('#server-status-jobs-wait').hide();
  $('#server-status-proc-count').hide();
  $('#server-status-avg-proc').hide();
  $('#server-status-avg-wait').hide();
}
</script>
<!-- 
<?php View::factory('common/version')->render(TRUE); ?>
SERVER is HTTPS PRESENT? <?= isset($_SERVER['HTTPS']) ?>
    <?php if(isset($_SERVER['HTTPS'])) { ?>
    VALUE= <?= isset($_SERVER['HTTPS']) ?>
<?php } ?>
 -->