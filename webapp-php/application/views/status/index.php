<?php slot::start('head') ?>
    <title>Server Status</title>
<?php slot::end() ?>

<h1 class="first">Server Status</h1>
<!-- params as <dt>key</dt><dd>value</dd> -->
<dl>
    <dt>LastReport</dt><dd><?php out::H($lastProcessedDate) ?></dd>
    <dt>ReportsInQueue</dt><dd><?php out::H($jobsPending) ?></dd>
    <dt>NumberOfProcessors</dt><dd><?php out::H($numProcessors) ?></dd>
    <dt>OldestQueuedJob</dt><dd><?php out::H($oldestQueuedJob) ?></dd>
    <dt>AverageProcessTime</dt><dd><?php out::H($avgProcessTime) ?></dd>
    <dt>AverageWaitTime</dt><dd><?php out::H($avgWaitTime) ?></dd>
</dl>
