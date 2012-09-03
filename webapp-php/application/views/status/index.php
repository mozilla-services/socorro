<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<?php slot::start('head') ?>
    <title>Server Status</title>
    <?php echo html::stylesheet(array(
       'css/flora/flora.all.css'
    ), 'screen')?>
    <!--[if IE]><?php echo html::script('js/flot-0.7/excanvas.pack.js') ?><![endif]-->
    <?php echo html::script(array(
        'js/jquery/plugins/ui/jquery.tablesorter.min.js',
        'js/flot-0.7/jquery.flot.pack.js',
        'js/timeago/jquery.timeago.js',
        'js/socorro/server_status.js'
    ))?>
<?php slot::end() ?>


<div class="page-heading">
	<h2>Server Status</h2>
</div>

<?php 
    $stat = $server_stats[0];
?>
<div class="panel">
<div class="title">As of <time class="timeago" datetime="<?php echo $stat->date_created ?>"><?php echo $stat->date_created ?></time></div>
    <div class="body">
        <table class="server_status">
            <tr>
                <td>Socorro revision</td><td><a href="https://github.com/mozilla/socorro/commit/<?php echo $server_stats['socorroRevision'] ?>"><?php echo $server_stats['socorroRevision'] ?></a></td>
            </tr>
            <tr>
                <td>Breakpad revision</td><td><a href="http://code.google.com/p/google-breakpad/source/browse/?r=<?php echo $server_stats['breakpadRevision'] ?>"><?php echo $server_stats['breakpadRevision'] ?></a></td>
            </tr>
            <tr>
                <td>Oldest job entered the queue</td><td><time class="timeago" datetime="<?php echo $stat->date_oldest_job_queued ?>"><?php echo $stat->date_oldest_job_queued ?></time></td>
            </tr>
            <tr>
                <td>Most recent job was completed</td><td><time class="timeago" datetime="<?php echo $stat->date_recently_completed ?>"><?php echo $stat->date_recently_completed ?></time></td>
            </tr>
        </table>
    </div>
</div>

<div class="panel">
    <div class="title">Graphs</div>
    <div class="body">
        <div class="server-status-graph">
          <h2>Enqueued Jobs</h2>
          <div id="server-status-graph-jobs-wait"></div>
        </div>
        <div class="server-status-graph">
          <h2>Mean time in queue</h2>
          <div id="server-status-graph-avg-wait"></div>
        </div>
        <div class="server-status-graph">
          <h2>Mean time to process a job</h2>
          <div id="server-status-graph-avg-proc"></div>
        </div>
        <div class="server-status-graph">
          <h2>Total number of processors</h2>
          <div id="server-status-graph-proc-count"></div>
        </div>
    </div>
</div>


<div class="panel">
    <div class="title">Latest Raw Stats</div>
    <div class="body">

<table id="server-stats-table" class="tablesorter data-table">
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
  var waiting_job_count = <?php echo json_encode($plotData['waiting_job_count']);?>;
  var processors_count = <?php echo json_encode($plotData['processors_count']);?>;
  var avg_process_sec = <?php echo json_encode($plotData['avg_process_sec']); ?>;
  var avg_wait_sec = <?php echo json_encode($plotData['avg_wait_sec']); ?>;
  var x_ticks = <?php echo json_encode( $plotData['xaxis_ticks']); ?>;
</script>
<!--
<?php View::factory('common/version')->render(TRUE); ?>
SERVER is HTTPS PRESENT? <?= isset($_SERVER['HTTPS']) ?>
    <?php if(isset($_SERVER['HTTPS'])) { ?>
    VALUE= <?= isset($_SERVER['HTTPS']) ?>
<?php } ?>
testing auto-svn update
 -->
