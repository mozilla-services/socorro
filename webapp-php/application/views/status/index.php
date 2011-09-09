<?php slot::start('head') ?>
    <title>Server Status</title>
    <?php echo html::stylesheet(array(
       'css/flora/flora.all.css'
    ), 'screen')?>
    <!--[if IE]><?php echo html::script('js/flot-0.7/excanvas.pack.js') ?><![endif]-->
    <?php echo html::script(array(
        'js/jquery/plugins/ui/jquery.tablesorter.min.js',
        'js/flot-0.7/jquery.flot.pack.js'
    ))?>
<?php slot::end() ?>


<div class="page-heading">
	<h2>Server Status</h2>
</div>


<?php $stat = $server_stats[0] ?>


<div class="panel">
    <div class="title">At a Glance</div>
    <div class="body">
        <table class="server_status">
            <tr>
                <td>Mood</td>
                <td><span class="server-status <?php echo $status ?>"><?php echo ucwords($status); ?></span></td>
            </tr>
            <tr>
                <td>Server Time</td><td><?= date('Y-m-d H:i:s', time()) ?></td>
            </tr>
            <tr>
                <td>Stats Created At</td><td><?php echo $stat->date_created ?></td>                
            </tr>
            <tr>
                <td>Waiting Jobs</td><td><?php echo $stat->waiting_job_count ?></td>
            </tr>
            <tr>
                <td>Processors Running</td><td><?php echo $stat->processors_count ?></td>
            </tr>
            <tr>
                <td>Average Seconds to Process</td><td><?php echo $stat->avg_process_sec ?></td>
            </tr>
            <tr>
                <td>Average Wait in Seconds</td><td><?php echo $stat->avg_wait_sec ?></td>
            </tr>
            <tr>
                <td>Recently Completed</td><td><?php echo $stat->date_recently_completed ?></td>
            </tr>
            <tr>
                <td>Oldest Job In Queue</td><td><?php echo $stat->date_oldest_job_queued ?></td>
            </tr>
            <tr>
                <td>Socorro revision</td><td><a href="https://github.com/mozilla/socorro/commit/<?php echo Kohana::config('revision.socorro_revision')?>"><?php echo Kohana::config('revision.socorro_revision')?></a></td>
            </tr>
        </table>
        
    </div>
</div>

<div class="panel">
    <div class="title">Graphs</div>
    <div class="body">

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
</div>


<div class="panel">
    <div class="title">Latest Raw Stats</div>
    <div class="body">

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

    </div>
</div>


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
     xaxis: { ticks: <?php echo json_encode( $plotData['xaxis_ticks'] ); ?> },
     yaxis: { labelWidth: 55 },
     shadowSize: 0

   });
  $.plot($("#server-status-graph-jobs-wait"),
   [{
      label:"Jobs Waiting",
      data: waiting_job_count
   }],
   { // options 
     xaxis: { ticks: <?php echo json_encode( $plotData['xaxis_ticks'] ); ?> },
     yaxis: { labelWidth: 55 },
     shadowSize: 0
   });

  $.plot($("#server-status-graph-proc-count"),
   [{
     label:"Proc Running",
     data: processors_count
   }], 
   { // options 
     xaxis: { ticks: <?php echo json_encode( $plotData['xaxis_ticks'] ); ?> },
     yaxis: { labelWidth: 55 },
     shadowSize: 0
   });

  $.plot($("#server-status-graph-avg-proc"),
   [{
     label:"Avg Process", 
     data: avg_process_sec
   }],
   { // options 
     xaxis: { ticks: <?php echo json_encode( $plotData['xaxis_ticks'] ); ?> },
     yaxis: { labelWidth: 55 },
     shadowSize: 0
   });

  $.plot($("#server-status-graph-avg-wait"),
   [{
     label:"Avg Wait",
     data: avg_wait_sec
   }],
   { 
     xaxis: { ticks: <?php echo json_encode( $plotData['xaxis_ticks'] ); ?> },
     yaxis: { labelWidth: 55 },
     shadowSize: 0
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
testing auto-svn update
 -->
