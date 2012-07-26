<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<?php slot::start('head') ?>
    <title>Top Crashers for <?php out::H($product . " " . $version) ?></title>
    <?php echo html::script(array(
        'js/jquery/plugins/ui/jquery.tablesorter.min.js',
        'js/socorro/topcrash.js',
        'js/socorro/bugzilla.js',
        'js/socorro/correlation.js'
    ))?>
    <?php echo html::stylesheet(array(
        'css/flora/flora.tablesorter.css'
    ), 'screen')?>
<?php slot::end() ?>

<div class="page-heading">
    <h2>Top Crashers for <?php out::H($product . " " . $version) ?></h2>
    <?php View::factory('common/tcbs_top_nav')->render(TRUE); ?>
</div>

<div class="panel">
    <div class="body notitle">
        <?php if (count($top_crashers) > 0) { ?>
            <p>Top <?php echo count($top_crashers) ?> Crashing Signatures for the build date range
                <time class="start-date"><?= $start_date ?></time> through
                <time class="end-date"><?= $end_date ?></time>.
            </p>
            <p>The report covers <span title="<?= $percent_total ?>" class="percentage"><?= number_format($percent_total * 100, 2)?>%</span>
                of all <?= $percent_total > 0 ? round($total_crashes / $percent_total) : $total_crashes ?> crashes during this period.
                Graphs below are dual-axis, having <strong>Count</strong> (Number of Crashes) on the left X axis and <strong>Percent</strong> of total of Crashes on the right X axis.
            </p>
        <?php } ?>
        <ul class="tc-duration-type tc-filter">
            <li class="tc-duration-heading">Type:</li>
            <?php foreach ($crash_types as $ct) { ?>
                <li><a href="<?= $crash_type_url . '/' . $ct ?>" <?php if ($ct == $crash_type) echo 'class="selected"'; ?>><?php echo ucfirst($ct); ?></a></li>
            <?php }?>
        </ul>
        <ul class="tc-duration-days tc-filter">
            <li class="tc-duration-heading">Days:</li>
            <?php foreach ($durations as $d) { ?>
                <li><a href="<?= $duration_url . '/' . $d . '/' . $crash_type; ?>" <?php if ($d == $duration) echo 'class="selected"'; ?>><?= $d ?></a></li>
            <?php }?>
        </ul>
        <ul class="tc-per-platform tc-filter">
            <li class="tc-per-platform-heading">OS:</li>
            <li><a href="<?= $duration_url . '/' . $duration . '/' . $crash_type; ?>" class="selected">All</a></li>
            <?php foreach ($platforms as $p) { ?>
                <li><a href="<?= $platform_url . '/' . $p . '/' . $duration . '/' . $crash_type . '/build'; ?>"><?= $p ?></a></li>
            <?php }?>
        </ul>
        <?php if (count($top_crashers) > 0) { ?>
        <table id="peros-tbl" class="tablesorter data-table">
            <thead>
                <th>Rank</th>
                <th title="The percentage of crashes against overall crash volume">%</th>
                <th title="The change in percentage since the report">Diff</th>
                <th>Signature</th>
                <th title="Crashes across platforms">Count</th>
                <th>Win</th>
                <th>Mac</th>
                <th>Lin</th>
                <th>Ver</th>
                <th>First Appearance</th>
                <?php if (isset($sig2bugs)) {?>
                <th>Bugzilla IDs</th>
                <?php } ?>
            </thead>
            <tbody>
            <?php
                $row = 1;

                foreach ($top_crashers as $crasher):
                $sigParams = array(
                            'range_value' => $range_value,
                            'range_unit'  => $range_unit,
                            'date'        => $end_date,
                            'signature'   => $crasher->signature
                );

                if (property_exists($crasher, 'missing_sig_param')) {
                    $sigParams['missing_sig'] = $crasher->{'missing_sig_param'};
                }

                if (property_exists($crasher, 'branch')) {
                    $sigParams['branch'] = $crasher->branch;
                } else {
                    $sigParams['version'] = $product . ':' . $version;
                }

                $link_url =  url::base() . 'report/list?' . html::query_string($sigParams);
            ?>
                <tr>
                    <td class="rank">
                        <?php out::H($row);
                        if ($crasher->trendClass == "up") { ?>
                            <span title="Movement in Rank since the <?= $start_date ?> report" class="moving-up"><?php echo $crasher->changeInRank ?></span>
                        <?php } else if($crasher->trendClass == "down") { ?>
                            <span title="Movement in Rank since the <?= $start_date ?> report" class="moving-down"><?php echo $crasher->changeInRank ?></span>
                        <?php } ?>
                    </td>
                    <td><?php out::H($crasher->{'display_percent'}) ?></td>
                    <td title="A change of <?php out::H($crasher->{'display_change_percent'})?> from <?php out::H($crasher->{'display_previous_percent'}) ?>">
                        <?php out::H($crasher->{'display_change_percent'}) ?>
                    </td>
                    <td><a class="signature" href="<?php out::H($link_url) ?>" title="<?php if (isset($crasher->display_full_signature)) out::H($crasher->display_full_signature); ?>">
                        <?= $crasher->display_signature; ?></a>
                        <?php
                        if ($crasher->{'display_null_sig_help'}) {
                            echo " <a href='http://code.google.com/p/socorro/wiki/NullOrEmptySignatures' class='inline-help'>Learn More</a> ";
                        } ?>
                        <div class="signature-icons">
                            <?php View::factory('common/tc_crash_types', array(
                                'crasher' => $crasher
                            ))->render(TRUE); ?>
                            <a href="#" title="Load graph data">
                                <img src="<?= url::site('/img/3rdparty/silk/chart_curve.png')?>" width="16" height="16" alt="Graph this" class="graph-icon" />
                            </a>
                        </div>
                        <div class="sig-history-legend"></div>
                        <p class="graph-close hide"><a href="javascript:void" title="Close graph">close x</a></p>
                        <div class="sig-history-graph"></div>
                        <input type="hidden" class='ajax-signature' name="ajax-signature-<?= $row ?>" value="<?= $crasher->{'display_signature'}?>" />
                    </td>
                    <td><?php out::H($crasher->count) ?></td>
                    <td><?php out::H($crasher->win_count) ?></td>
                    <td><?php out::H($crasher->mac_count) ?></td>
                    <td><?php out::H($crasher->linux_count) ?></td>
                    <td><span title="<?php if (isset($crasher->versions)) out::H($crasher->versions); ?>"><?php
                        if (isset($crasher->versions_count) && !empty($crasher->versions_count)) {
                            out::H($crasher->versions_count);
                        } else {
                            echo "-";
                        }
                    ?></span></td>
                    <td <?php if (isset($crasher->first_report_exact)) { ?>
                            title="This crash signature first appeared at <?php out::H($crasher->first_report_exact); ?>"
                        <?php } ?>>
                        <?php if (isset($crasher->first_report)) { out::H($crasher->first_report); } ?>
                    </td>
                    <?php 
                        if (isset($sig2bugs)) {
                            View::factory('common/tc_bugzilla', array(
                                'crasher' => $crasher,
                                'sig2bugs' => $sig2bugs
                            ))->render(TRUE);
                        }
                    ?>
                </tr>
            <?php
                $row += 1; 
                endforeach 
            ?>
            </tbody>
        </table>
        <?php View::factory('common/csv_link_copy')->render(TRUE); ?>
    </div>
    <!--[if IE]><?php echo html::script('js/flot-0.7/excanvas.pack.js') ?><![endif]-->
    <?php
        echo html::script(array('js/flot-0.7/jquery.flot.pack.js'));
        $partial_url_path = '/' . join('/', array_map('rawurlencode', array($product, $version))) . '/';
    ?>
    <script type="text/javascript">//<![CDATA[
        var SocAjax = '<?= url::site('topcrasher/plot_signature') . '/' . $product . '/' . $version . '/'; ?>',
        SocAjaxStartEnd = '<?= '/' . $start_date . '/' . $end_date . '/'; ?>',
        SocImg = '<?= url::site('img') ?>/',
        SocReport = {
            base: '<?= url::site('/correlation/bulk_ajax') ?>/',
            path: '<?= $partial_url_path ?>',
            loading: 'Loading <?= html::image( array('src' => 'img/loading.png', 'width' => '16', 'height' => '17')) ?>'
        };//]]>
    </script>
    <?php } else { ?>
        <p class="no-results">No crashing signatures found for the period <time><?= $start_date ?></time> to <time><?= $end_date ?></time></p>
    <?php } ?>
</div>
