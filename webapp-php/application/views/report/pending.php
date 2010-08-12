
<div id="checking" class="pendingStatus">
    <form><input type="hidden" id="count" name="count" value="0" /></form>
    <h3>Please Wait...</h3>
    <p>Fetching this archived report will take 30 seconds to 5 minutes</p>
    <img src="<?php echo url::site(); ?>img/ajax-loader.gif">
    <p id="next_attempt">Next attempt in <span id="counter" name="counter">30</span> seconds...</p> 
    <p id="processing" class="pendingProcessing" style="display:none">Querying for archived report...</p>
</div>

<script type="text/javascript" src="<?php echo url::site(); ?>js/socorro/pending.js"></script>
<script type="text/javascript">
document.onload = pendingReportTimer("<?php echo html::specialchars($url_ajax); ?>");
</script>

