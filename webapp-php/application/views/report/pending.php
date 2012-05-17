/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */


<?php if (empty($status)) { ?>

	<div id="checking" class="pendingStatus">
	    <form><input type="hidden" id="count" name="count" value="0" /></form>
	    <h3>Please Wait...</h3>
	    <p>Fetching this archived report will take 30 seconds to 5 minutes</p>
	    <img src="<?php echo url::site(); ?>img/ajax-loader.gif">
	    <p id="next_attempt">Next attempt in <span id="counter" name="counter">30</span> seconds...</p>
	    <p id="processing" class="pendingProcessing" style="display:none">Querying for archived report...</p>
	</div>

	<div id="fail" class="pendingStatus" style="display:none;">
	    <h3>Oh Noes!</h3>
	    <p>This archived report could not be located.</p>
	</div>

	<script type="text/javascript" src="<?php echo url::site(); ?>js/socorro/pending.js"></script>
	<script type="text/javascript">
	document.onload = pendingReportTimer("<?php echo html::specialchars($url_ajax); ?>");
	</script>

<?php } elseif ($status == 410) { ?>

	<div id="fail" class="pendingStatus">
	    <h3>Oh Noes!</h3>
	    <p>This archived report has expired because it is greater than 3 years of age.</p>
	</div>
<?php } ?>


<?php if ($job): ?>
    <h2>Queue Info</h2>
    <dl>
        <dt>ID</dt>
            <dd><?php out::H( $job->uuid ) ?></dd>
        <dt>Time Queued</dt>
            <dd><?php out::H( $job->queueddatetime ) ?></dd>
        <?php if ($job->starteddatetime): ?>
            <dt>Time Started</dt>
                <dd><?php out::H( $job->starteddatetime ) ?></dd>
        <?php endif ?>
        <?php if ($job->message): ?>
            <dt>Message</dt>
                <dd><?php out::H( $job->message ) ?></dd>
        <?php endif ?>
    </dl>
<?php endif ?>


