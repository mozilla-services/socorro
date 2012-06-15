<?php slot::start('head') ?>
    <?php
        $report_for = $report_product . " " . $version;
    ?>
    <title>Crash Trends Report For <?= $report_for ?></title>
    <?php echo html::stylesheet(array(
    'css/jquery-ui-1.8.16/flick/jquery-ui-1.8.16.custom.css',
    'css/crash_trends.css'), 'screen')?>
    <!--[if IE]><?php echo html::script('js/flot-0.7/excanvas.pack.js') ?><![endif]-->
    
    
    <script type="text/javascript">
        var json_path = "<?= $data_url ?>",
        init_prod = "<?= $report_product ?>",
        init_ver = "<?= $version ?>";
    </script>
    
<?php slot::end() ?>

<div class="page-heading">
    <h2>Nightly Crash Trends For <?php out::H($report_for) ?></h2>
</div>

<div class="crash_stats_panel report_criteria">
    <form name="nightly_crash_trends" id="nightly_crash_trends" action="<?php echo $data_url ?>" method="get">
        <h3 class="crash_stats_panel_title">Select Report Criteria</h3>
        <div class="info"></div>
        <div class="error"></div>
        <fieldset class="crash_stats_body">
            <div class="field">
                <label for="start_date">From</label>
                <input type="date" name="start_date" id="start_date" required />
            </div>
            
            <div class="field">
                <label for="end_date">To</label>
                <input type="date" name="end_date" id="end_date" required />
            </div>
            
            <div class="field">
                <label for="product">Product</label>
                <select name="product" id="product">
                    <option value="none">Select A Product</option>
                    <?php foreach ($report_products as $product_name) { ?>
                    <option value="<?php out::H($product_name) ?>"><?php out::H($product_name) ?></option>
                    <?php } ?>
                </select>
            </div>
            
            <div class="field">
                <label for="version">Version</label>
                <select name="version" id="version"></select>
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
   'js/socorro/utils.js',
   'js/socorro/crash_trends.js'
))?>