<?php if (count($top_crashers) > 0) { ?>
<div>
    Top <?php echo count($top_crashers) ?> Crashing Signatures.
    <time class="start-date"><?= $start ?></time> through
    <time class="end-date"><?= $last_updated ?></time>.
	<p>The report covers <span class="percentage" title="<?=$percentTotal?>"><?= number_format($percentTotal * 100, 2)?>%</span> of all <?= $percentTotal > 0 ? round($total_crashes / $percentTotal) : $total_crashes ?> crashes during this period. Graphs below are dual-axis, having <strong>Count</strong> (Number of Crashes) on the left X axis and <strong>Percent</strong> of total of Crashes on the right X axis.</p>
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
            <li><a href="<?= $platform_url . '/' . $p . '/' . $duration . '/' . $crash_type; ?>"><?= $p ?></a></li>
        <?php }?>
    </ul>
<?php if (count($top_crashers) > 0) { ?>
        <table id="signatureList" class="tablesorter">
            <thead>
                <tr>
                    <th>Rank</th>
	            <th title="The percentage of crashes against overall crash volume">%</th>
	            <th title="The change in percentage since the <?= $start ?> report">Diff</th>
                    <th>Signature</th>
                    <th title="Crashes across platforms">Count</th>
                    <th>Win</th>
                    <th>Mac</th>
                    <th>Lin</th>
                    <th>Ver</th>
                    <th>First Appearance</th>
           <?php if (isset($sig2bugs)) {?>
               <th class="bugzilla_numbers">Bugzilla IDs</th>
           <?php } ?>
                    <th title="Does not imply Causation">Correlation</th>
                </tr>

            </thead>
            <tbody>
                <?php $row = 1 ?>
                <?php foreach ($top_crashers as $crasher): ?>
                    <?php
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
                                <span title="Movement in Rank since the <?= $start ?> report" class="moving-up"><?php echo $crasher->changeInRank ?></span>
                            <?php } else if($crasher->trendClass == "down") { ?>
                                <span title="Movement in Rank since the <?= $start ?> report" class="moving-down"><?php echo $crasher->changeInRank ?></span>
                            <?php } ?>
                        </td>
			 <td><?php out::H($crasher->{'display_percent'}) ?></td>
			 <td title="A change of <?php out::H($crasher->{'display_change_percent'})?> from <?php out::H($crasher->{'display_previous_percent'}) ?>"><?php out::H($crasher->{'display_change_percent'}) ?></td>
			 <td><a class="signature" href="<?php out::H($link_url) ?>" title="<?= $crasher->display_full_signature; ?>"><?= $crasher->display_signature; ?></a><?php
			 if ($crasher->{'display_null_sig_help'}) {
			     echo " <a href='http://code.google.com/p/socorro/wiki/NullOrEmptySignatures' class='inline-help'>Learn More</a> ";
			 } ?>
                <div class="signature-icons">
                    <?php View::factory('common/tc_crash_types', array(
                    'crasher' => $crasher
                    ))->render(TRUE); ?>
                    <a href="#" title="Load graph data"><img src="<?= url::site('/img/3rdparty/silk/chart_curve.png')?>" width="16" height="16" alt="Graph this" class="graph-icon" /></a>
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
                        <td <?php if (isset($crasher->first_report_exact)) { ?>title="This crash signature first appeared at <?php out::H($crasher->first_report_exact); ?>" <?php } ?>>
                            <?php if (isset($crasher->first_report)) { out::H($crasher->first_report); } ?>
                        </td>

                        <?php 
                            if (isset($sig2bugs)) {
                                View::factory('common/tc_bugzilla', array(
                                    'crasher' => $crasher,
                                    'sig2bugs' => $sig2bugs
                                ))->render(TRUE);
                            }
                        
                            View::factory('common/tc_correlations', array(
                                'crasher' => $crasher,
                                'row'     => $row
                            ))->render(TRUE);
                        ?>
                    </tr>
                    <?php
                        $row += 1; 
                        endforeach 
                    ?>
            </tbody>
        </table>
    </div>
    <!--[if IE]><?php echo html::script('js/flot-0.7/excanvas.pack.js') ?><![endif]-->
    <?php echo html::script(array(
        'js/flot-0.7/jquery.flot.pack.js'
				));
    $partial_url_path = '/' . join('/', array_map('rawurlencode', array($product, $version))) . '/';
?>
    <script type="text/javascript">//<![CDATA[
    var SocAjax = '<?= url::site('topcrasher/plot_signature') . '/' . $product . '/' . $version . '/'; ?>';
	var SocAjaxStartEnd = '<?= '/' . $start . '/' . $last_updated . '/'; ?>';
    var SocImg = '<?= url::site('img') ?>/';
     var SocReport = {
          base: '<?= url::site('/correlation/bulk_ajax') ?>/',
          path: '<?= $partial_url_path ?>',
	  loading: 'Loading <?= html::image( array('src' => 'img/loading.png', 'width' => '16', 'height' => '17')) ?>'
      };
//]]></script>
    <?php View::factory('common/csv_link_copy')->render(TRUE); ?>
<?php } else { ?>
    <p class="no-results">No crashing signatures found for the period <time><?= $start ?></time> to <time><?= $last_updated ?></time></p>
<?php } ?>
