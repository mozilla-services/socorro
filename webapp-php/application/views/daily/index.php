<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<?php slot::start('head') ?>
    <title>Crashes per Active Daily User for <?php out::H($product) ?></title>
    <link title="CSV formatted Crashes per Active Daily User for <?php out::H($product) ?>" type="text/csv" rel="alternate" href="<?php out::H($url_csv); ?>" />

<?php
    echo html::stylesheet(array(
    'css/jquery-ui-1.8.16/flick/jquery-ui-1.8.16.custom.css',
    'css/daily.css',
    ), array('screen', 'screen'));
?>
<?php slot::end() ?>

<?php
    echo '<script>var data = ' . json_encode($graph_data) . ";\n";
    if ($form_selection == 'by_report_type') {?>
        window.socGraphByReportType = true;
<?php } else { ?>
        window.socGraphByReportType = false;
<?php } ?>
    </script>
<?php
echo html::script(array(
    'js/jquery/plugins/ui/jquery-ui-1.8.16.custom.min.js',
    'js/flot-0.7/jquery.flot.pack.js',
    'js/socorro/daily.js',
));
?>

<div class="page-heading">
    <h2>Crashes per Active Daily User</h2>
</div>

<?php
    View::factory('daily/daily_search', array(
    'date_start' => $date_start,
    'date_end' => $date_end,
    'duration' => $duration,
    'form_selection' => $form_selection,
    'graph_data' => $graph_data,
    'operating_system' => $operating_system,
    'operating_systems' => $operating_systems,
    'product' => $product,
    'products' => $products,
    'hang_type' => $hang_type,
    'url_form' => $url_form,
    'versions' => $versions
    ))->render(TRUE);
?>

<div class="panel daily_graph">
    <div class="title">
        <h2>Crashes per 100 ADUs</h2>
    </div>

    <div class="body">
    <?php if ((isset($graph_data['count']) && $graph_data['count'] > 0) || !empty($graph_data)) { ?>
        <div id="adu-chart"></div>
        <p class="adu-chart-help">This graph uses an approximate <a href="https://wiki.mozilla.org/Socorro/SocorroUI/Branches_Admin#Throttle">throttle value</a> for each version, which may not be completely accurate for the entire time period.</p>
        <div id="adu-chart-legend"></div>
    <?php } else { ?>
        <p>No Active Daily User crash data is available for this report.</p>
    <?php } ?>
    </div>
</div>

<br class="clear" />

<?php
if (!empty($graph_data)) {
    View::factory($file_crash_data, array(
        'dates' => $dates,
        'date_range_type' => $date_range_type,
        'operating_systems' => $operating_systems,
        'versions_in_result' => $versions_in_result,
        'statistics' => $statistics,
        'url_csv' => $url_csv,
        'versions' => $versions
    ))->render(TRUE);
}
?>
