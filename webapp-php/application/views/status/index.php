<?php slot::start('head') ?>
    <title>Server Status</title>
    <?php echo html::stylesheet(array(
       'css/flora/flora.all.css'
    ), 'screen')?>
    <?php echo html::script(array(
        'js/jquery/jquery-1.2.1.js',
        'js/jquery/plugins/ui/jquery.tablesorter.min.js',
        'js/flot-0.5/jquery.flot.pack.js'
    ))?>
<?php slot::end() ?>

<h1 class="first">Server Status - <span class="<?php echo $status ?>"><?php echo ucwords($status); ?></span></h1>
<?php $stat = end($server_stats) ?>

  <div id="at-a-glance">
    <h2>At a Glance</h2>
        <dl>
      <dt>Time</dt>
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
  <div id="toc">
    <h2 class="first">Graphs</h2>
    <ul>
    <li><a href="#server-status-comb">Combined server status</a></li>
    <li><a href="#server-status-jobs-wait">Total number of jobs waiting</a></li>
    <li><a href="#server-status-proc-count">Total number of processors</a></li>
    <li><a href="#server-status-avg-proc">Average time to process a job</a></li>
    <li><a href="#server-status-avg-wait">Average time a job waits</a></li>



    </ul>
  </div>
<br style="clear:both;" />
<h3 id="server-status-comb">Combined Server Stats</h3>
<div id="server-status-graph-comb" style="width:800px;height:300px;"></div>
<div class="caption server-plot-label">Combined server status in 10 minute intervals. Measurements on left are for counts and the measurements on the right are in seconds</div>

<h3 id="server-status-jobs-wait">Total number of jobs waiting</h3>
<div id="server-status-graph-jobs-wait" style="width:800px;height:300px;"></div>

<h3 id="server-status-proc-count">Total number of processors running against job queue</h3>
<div id="server-status-graph-proc-count" style="width:800px;height:300px;"></div>

<h3 id="server-status-avg-proc">Average time to process a job in seconds</h3>
<div id="server-status-graph-avg-proc" style="width:800px;height:300px;"></div>

<h3 id="server-status-avg-wait">Average time a job waits until processed in seconds</h3>
<div id="server-status-graph-avg-wait" style="width:800px;height:300px;"></div>

<script id="source" language="javascript" type="text/javascript">
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
}); 
</script>
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
