<?php if (count($top_crashers) > 0) { ?>
<div>
    Top <?php echo count($top_crashers) ?> Crashing Signatures.
    <span class="start-date"><?= $start ?></span> through
    <span class="end-date"><?= $last_updated ?></span>.
	<p>The report covers <span class="percentage" title="<?=$percentTotal?>"><?= number_format($percentTotal * 100, 2)?>%</span> of all <?= $percentTotal > 0 ? round($total_crashes / $percentTotal) : $total_crashes ?> crashes during this period. Graphs below are dual-axis, having <strong>Count</strong> (Number of Crashes) on the left X axis and <strong>Percent</strong> of total of Crashes on the right X axis.</p>

    <ul class="tc-duration-type">
        <li class="tc-duration-heading">Type:</li>
        <?php foreach ($crash_types as $ct) { ?>
            <li><a href="<?= $crash_type_url . '/' . $ct ?>" <?php if ($ct == $crash_type) echo 'class="selected"'; ?>><?php echo ucfirst($ct); ?></a></li>
        <?php }?>
    </ul>
    <ul class="tc-duration-days">
        <li class="tc-duration-heading">Days:</li>
        <?php foreach ($durations as $d) { ?>
            <li><a href="<?= $duration_url . '/' . $d . '/' . $crash_type; ?>" <?php if ($d == $duration) echo 'class="selected"'; ?>><?= $d ?></a></li>
        <?php }?>
    </ul>

        <table id="signatureList" class="tablesorter">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th title="Movement in Rank since the <?= $start ?> report">Trend</th>
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
                    <tr class="<?php echo ( ($row-1) % 2) == 0 ? 'even' : 'odd' ?>">
                        <td class="rank"><?php out::H($row) ?></td>
                        <td><div class="trend <?= $crasher->trendClass ?>"><?php echo $crasher->changeInRank ?></div></td>
			 <td><span class="percentOfTotal"><?php out::H($crasher->{'display_percent'}) ?></span></td>
			 <td><div title="A change of <?php out::H($crasher->{'display_change_percent'})?> from <?php out::H($crasher->{'display_previous_percent'}) ?>"
                                ><?php out::H($crasher->{'display_change_percent'}) ?></div></td>
			 <td><a class="signature" href="<?php out::H($link_url) ?>"
                                title="View reports with this crasher."><span><?php out::H($crasher->{'display_signature'}) ?></span></a><?php
			 if ($crasher->{'display_null_sig_help'}) {
			     echo " <a href='http://code.google.com/p/socorro/wiki/NullOrEmptySignatures' class='inline-help'>Learn More</a> ";
			 } ?>
                         <div class="signature-icons">
                         <?php
							$linked = false;
							if (isset($crasher->{'link'}) && !empty($crasher->{'link'})) {
							    $linked = true;
							}
							if (isset($crasher->{'content_count'}) && $crasher->{'content_count'} > 0) { ?>
							    <?php if ($linked) { ?><a href="<?= $crasher->{'link'} ?>" class="content-btn" title="Content Crash"><?php } ?><img src="<?= url::site('/img/3rdparty/fatcow/content16x16.png')?>" width="16" height="16" alt="Content Crash" title="Content Crash" class="content" /><?php if ($linked) { echo '</a>'; } ?>
							<?php } ?>
							<?php if ($crasher->{'hang_count'} > 0) { ?>
							    <?php if ($linked) { ?><a href="<?= $crasher->{'link'} ?>" class="hang-pair-btn" title="Hanged Crash"><?php } ?><img src="<?= url::site('/img/3rdparty/fatcow/stop16x16.png')?>" width="16" height="16" alt="Hanged Crash" title="Hanged Crash" class="hang" /><?php if ($linked) { echo '</a>'; } ?>
							<?php } ?>
						    <?php if ($crasher->{'plugin_count'} > 0) {?>
						              <?php if ($linked) { ?><a href="<?= $crasher->{'link'} ?>" class="plugin-btn" title="Plugin Crash"><?php } ?><img src="<?= url::site('/img/3rdparty/fatcow/brick16x16.png')?>" width="16" height="16" alt="Plugin Crash" title="Plugin Crash" class="plugin" class="plugin" /><?php if ($linked) { echo '</a>'; } ?>
						    <?php } ?>
						    <?php if ($crasher->{'count'} > $crasher->{'plugin_count'}) { ?>
						      <?php if ($linked) { ?><a href="<?= $crasher->{'link'} ?>" class="hang-pair-btn" title="Browser Crash"><?php } ?><img src="<?= url::site('/img/3rdparty/fatcow/application16x16.png')?>" width="16" height="16" alt="Browser Crash" title="Browser Crash" class="browser" /><?php if ($linked) { echo '</a>'; } ?>
                            <?php } ?>


                         <a href="#"><img src="<?= url::site('/img/3rdparty/silk/chart_curve.png')?>" width="16" height="16" alt="Graph this" class="graph-icon" /></a>
                         </div>
<div class="sig-history-graph"></div><div class="sig-history-legend"></div><input type="hidden" class='ajax-signature' name="ajax-signature-<?= $row ?>" value="<?= $crasher->{'display_signature'}?>" /></td>
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
                        <td><span title="This crash signature first appeared at <?php if (isset($crasher->first_report_exact)) out::H($crasher->first_report_exact); ?>"><?php
                            if (isset($crasher->first_report)) out::H($crasher->first_report); ?></span></td>

               <?php if (isset($sig2bugs)) {?>
                    <td>
		    <?php if (array_key_exists($crasher->signature, $sig2bugs)) {
			      $bugs = $sig2bugs[$crasher->signature];
			      for ($i = 0; $i < 3 and $i < count($bugs); $i++) {
				  $bug = $bugs[$i];
				  View::factory('common/bug_number')->set('bug', $bug)->render(TRUE);
				  echo ", ";
			      } ?>
                              <div class="bug_ids_extra">
                        <?php for ($i = 3; $i < count($bugs); $i++) {
				  $bug = $bugs[$i];
                                  View::factory('common/bug_number')->set('bug', $bug)->render(TRUE);
                              } ?>
			      </div>
			<?php if (count($bugs) > 0) { ?>
			      <a href='#' title="Click to See all likely bug numbers" class="bug_ids_more">More</a>
                            <?php View::factory('common/list_bugs', array(
						      'signature' => $crasher->signature,
						      'bugs' => $bugs,
						      'mode' => 'popup'
				  ))->render(TRUE);
		              }
                         } ?>
                    </td>
               <?php } ?>
       <?php if ($crasher->{'display_signature'} == Crash::$empty_sig ||
                 $crasher->{'display_signature'} == Crash::$null_sig) { ?>
                   <td>N/A</td>
       <?php } else { ?>
                   <td class="correlation-cell">
                       <div id="correlation-panel<?=$row?>">
                           <div class="top"><span></span></div><a class="correlation-toggler" href="#">Show More</a>
                           <div class="complete">
			      <h3>Based on <span class='osname'><?= $crasher->{'correlation_os'} ?></span> crashes</h3>
			      <div class="correlation-module"><h3>CPU</h3><div class="cpus"></div></div>
                              <div class="correlation-module"><h3>Add-ons</h3><div class="addons"></div></div>
                              <div class="correlation-module"><h3>Modules</h3><div class="modules"></div></div>
                           </div>
                       </div></td>
       <?php } ?>
                        <?php $row+=1 ?>
                    </tr>
                <?php endforeach ?>
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
    <p>No results were found.</p>
<?php } ?>
