<?php slot::start('head') ?>
    <title>New Report for ...</title>
    <?php echo html::stylesheet(array('css/crash_trends.css'), 'screen')?>
    <!--[if IE]><?php echo html::script('js/flot-0.7/excanvas.pack.js') ?><![endif]-->
<?php slot::end() ?>

<div class="page-heading">
    <h2>Crash Trends</h2>
</div>

<form name="nightly_crash_trends" id="nightly_crash_trends" action="/" method="get">
    <fieldset>
        <legend>Select Report Criteria</legend>
        
        <h4>Date Range</h4>
        <div class="field">
            <label for="from_date">From</label>
            <input type="date" name="from_date" id="from_date" />
        </div>
        
        <div class="field">
            <label for="to_date">To</label>
            <input type="date" name="to_date" id="to_date" />
        </div>
        
        <div class="field">
            <label for="version">Version</label>
            <select name="version" id="version">
                <option value="5.0a2">5.0a2</option>
                <option value="6.0a2">6.0a2</option>
            </select>
        </div>
        
        <input type="submit" name="generate" value="Generate" />
    </fieldset>
</form>
<div id="graph_legend"></div>
<div id="nightly_crash_trends_graph"></div>


<?php echo html::script(array(
   'js/flot-0.7/jquery.flot.pack.js',
   'js/socorro/crash_trends.js'
))?>