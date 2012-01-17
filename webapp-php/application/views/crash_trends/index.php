<?php slot::start('head') ?>
    <title>New Report for ...</title>
    <?php echo html::stylesheet(array(
    'css/jquery-ui-1.8.16/flick/jquery-ui-1.8.16.custom.css',
    'css/crash_trends.css'), 'screen')?>
    <!--[if IE]><?php echo html::script('js/flot-0.7/excanvas.pack.js') ?><![endif]-->
<?php slot::end() ?>

<div class="page-heading">
    <h2>Crash Trends</h2>
</div>

<div class="crash_stats_panel report_criteria">
    <form name="nightly_crash_trends" id="nightly_crash_trends" action="/" method="get">
        <h3 class="crash_stats_panel_title">Select Report Criteria</h3>
        <div class="error"></div>
        <fieldset class="crash_stats_body">
            <div class="field">
                <label for="from_date">From</label>
                <input type="date" name="from_date" id="from_date" required />
            </div>
            
            <div class="field">
                <label for="to_date">To</label>
                <input type="date" name="to_date" id="to_date" required />
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
</div>

<div class="crash_stats_panel report_graph">
    <figure>
        <figcaption class="crash_stats_panel_title">Crash Trends From <time id="fromdate"></time> To <time id="todate"></time></figcaption>
        <div class="crash_stats_body">
            <div id="graph_legend"></div>
            <ul id="dates"></ul>
            <div id="nightly_crash_trends_graph"></div>
        </div>
    </figure>
</div>


<?php echo html::script(array(
   'js/flot-0.7/jquery.flot.pack.js',
   'js/flot-0.7/jquery.flot.stack.js',
   'js/jquery/plugins/ui/jquery-ui-1.8.16.custom.min.js',
   'js/jquery/plugins/jquery.mockjax.js',
   'js/socorro/utils.js',
   'js/socorro/crash_trends.js'
))?>