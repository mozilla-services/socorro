<div class="panel daily_">
	<div class="title">
		<h2>Crashes per ADU by Report Type</h2>
		<div class="choices">
			<ul>
				<li><a href="<?php echo $url_csv; ?>">csv</a></li>
			</ul>
		</div>
    </div>

    <div class="body">

	<?php if (isset($results->versions) && isset($versions) && !empty($versions)) { ?>

		<table id="crash_data" class="crash_data">
			<tr>
				<th class="date" rowspan="2">Date</th>
				<?php foreach ($versions as $key => $version) { ?>
					<?php if (!empty($version)) { ?>
						<th class="version" colspan="<?= 2 + (count($statistic_keys) * 2) ?>"><?php out::H($version); ?></th>
					<?php } ?>
				<?php } ?>
				</tr>
				<tr>
				<?php foreach ($versions as $version) { ?>
					<?php if (!empty($version)) { ?>
						<th class="stat">ADU</th>
						<th class="stat" title="The throttle rate is the effective throttle rate - the combined throttle rate for client-side throttling and server-side throttling.">Throttle</th>
				            <?php if (in_array('crashes', $statistic_keys)) { ?>
						    <th class="stat">Crashes</th>
						    <th class="stat">Crash Ratio</th>
					    <?php } ?>
                                            <?php if (in_array('oopp', $statistic_keys)) { ?>
						    <th class="stat">OOPP</th>
						    <th class="stat">OOPP Ratio</th>
					    <?php } ?>
                                            <?php if (in_array('hang_browser', $statistic_keys)) { ?>
						    <th class="stat">Hang Browser</th>
						    <th class="stat">Hang Browser Ratio</th>
					    <?php } ?>
                                            <?php if (in_array('hang_plugin', $statistic_keys)) { ?>
						    <th class="stat">Hang Plugin</th>
						    <th class="stat">Hang Plugin Ratio</th>
					    <?php } ?>
					<?php } ?>
				<?php } ?>
			</tr>

			<?php foreach ($dates as $date) { ?>
				<tr>
					<td><?php out::H($date); ?></td>

					<?php
						$i = 0;
						foreach ($results->versions as $version) {
							if ($version->version == $versions[$i]) {
								$key = $version->version;
					?>

								<td><?php
									if (isset($statistics['versions'][$key][$date]['users'])) {
										out::H(number_format(round($statistics['versions'][$key][$date]['users'])));
									} else {
										echo '-';
									}
								?></td>
								<td title="The throttle rate is the effective throttle rate - the combined throttle rate for client-side throttling and server-side throttling."><?php
							        if (isset($statistics['versions'][$key][$date]['throttle'])) {
							        	out::H($statistics['versions'][$key][$date]['throttle'] * 100);
							        	echo '%';
							        } else {
							        	echo '-';
							        }
								?></td>
                                                                <?php if (in_array('crashes', $statistic_keys)) { ?>
<td><?php
									    if (isset($statistics['versions'][$key][$date]['crashes'])) {
										out::H(number_format(round($statistics['versions'][$key][$date]['crashes'])));
									    } else {
										echo '-';
									    }
								    ?></td>
								    <td><?php
									    if (isset($statistics['versions'][$key][$date]['ratio'])) {
										$ratio = round($statistics['versions'][$key][$date]['ratio'] * 100, 2);
										out::H($ratio);
										echo "%";
									    } else {
										echo '-';
									    }
								    ?></td>
					<?php
								} // if in_array crashes
                                                                if (in_array('oopp', $statistic_keys)) { ?>
<td><?php
									    if (isset($statistics['versions'][$key][$date]['oopp'])) {
										out::H(number_format(round($statistics['versions'][$key][$date]['oopp'])));
									    } else {
										echo '-';
									    }
								    ?></td>
								    <td><?php
									    if (isset($statistics['versions'][$key][$date]['oopp_ratio'])) {
										$oopp_ratio = round($statistics['versions'][$key][$date]['oopp_ratio'] * 100, 2);
										out::H($oopp_ratio);
										echo "%";
									    } else {
										echo '-';
									    }
								    ?></td>
					<?php
								} // if in_array oopp
                                                                if (in_array('hang_browser', $statistic_keys)) { ?>
<td><?php
									    if (isset($statistics['versions'][$key][$date]['hang_browser'])) {
										out::H(number_format(round($statistics['versions'][$key][$date]['hang_browser'])));
									    } else {
										echo '-';
									    }
								    ?></td>
								    <td><?php
									    if (isset($statistics['versions'][$key][$date]['hang_browser_ratio'])) {
										$hang_browser_ratio = round($statistics['versions'][$key][$date]['hang_browser_ratio'] * 100, 2);
										out::H($hang_browser_ratio);
										echo "%";
									    } else {
										echo '-';
									    }
								    ?></td>
					<?php
								} // if in_array hang_browser
                                                                if (in_array('hang_plugin', $statistic_keys)) { ?>
<td><?php
									    if (isset($statistics['versions'][$key][$date]['hang_plugin'])) {
										out::H(number_format(round($statistics['versions'][$key][$date]['hang_plugin'])));
									    } else {
										echo '-';
									    }
								    ?></td>
								    <td><?php
									    if (isset($statistics['versions'][$key][$date]['hang_plugin_ratio'])) {
										$hang_plugin_ratio = round($statistics['versions'][$key][$date]['hang_plugin_ratio'] * 100, 2);
										out::H($hang_plugin_ratio);
										echo "%";
									    } else {
										echo '-';
									    }
								    ?></td>
					<?php
								} // if in_array hang_plugin
								$i++;
							}
						}
					?>
				</tr>
			<?php } ?>

			<tr>
				<td class="date"><strong>Total</strong></td>
			<?php
				$i = 0;
				foreach($results->versions as $version) {
					if ($version->version == $versions[$i]) {
						$key = $version->version;
?>
<td class="stat"><strong><?php
					if (isset($statistics['versions'][$key]['users'])) {
						out::H(number_format(round($statistics['versions'][$key]['users'])));
					}
				?></strong></td>
<td class="stat" title="The throttle rate is the effective throttle rate - the combined throttle rate for client-side throttling and server-side throttling."><strong><?php
					if (isset($statistics['versions'][$key]['throttle'])) {
						out::H($statistics['versions'][$key]['throttle'] * 100);
						echo '%';
					}
				?></strong></td>



<?php
						if (in_array('crashes', $statistic_keys)) {
			?>


				                    <td class="stat"><strong><?php
					            if (isset($statistics['versions'][$key]['crashes'])) {
						        out::H(number_format(round($statistics['versions'][$key]['crashes'])));
					            } ?></strong></td>
                                                    <td class="stat"><strong><?php
					            if (isset($statistics['versions'][$key]['ratio'])) {
						        $ratio = round($statistics['versions'][$key]['ratio'] * 100, 2);
						        out::H($ratio);
						        echo "%";
					            }
				                    ?></strong></td>
				          <?php }//if in_array crashes
						if (in_array('oopp', $statistic_keys)) { ?>
                                                    <td class="stat"><strong><?php
					            if (isset($statistics['versions'][$key]['oopp'])) {
						        out::H(number_format(round($statistics['versions'][$key]['oopp'])));
					            } ?></strong></td>
                                                    <td class="stat"><strong><?php
					            if (isset($statistics['versions'][$key]['oopp_ratio'])) {
						        $oopp_ratio = round($statistics['versions'][$key]['oopp_ratio'] * 100, 2);
						        out::H($oopp_ratio);
						        echo "%";
					            }
				                    ?></strong></td>
					  <?php }//if in_array oopp
                                          if (in_array('hang_browser', $statistic_keys)) { ?>
                                                    <td class="stat"><strong><?php
					            if (isset($statistics['versions'][$key]['hang_browser'])) {
						        out::H(number_format(round($statistics['versions'][$key]['hang_browser'])));
					            } ?></strong></td>
                                                    <td class="stat"><strong><?php
					            if (isset($statistics['versions'][$key]['hang_browser_ratio'])) {
						        $hang_browser_ratio = round($statistics['versions'][$key]['hang_browser_ratio'] * 100, 2);
						        out::H($hang_browser_ratio);
						        echo "%";
					            }
				                    ?></strong></td>
					  <?php }//if in_array hang_browser
                                                    if (in_array('hang_plugin', $statistic_keys)) { ?>
                                                    <td class="stat"><strong><?php
					            if (isset($statistics['versions'][$key]['hang_plugin'])) {
						        out::H(number_format(round($statistics['versions'][$key]['hang_plugin'])));
					            } ?></strong></td>
                                                    <td class="stat"><strong><?php
					            if (isset($statistics['versions'][$key]['hang_plugin_ratio'])) {
						        $hang_plugin_ratio = round($statistics['versions'][$key]['hang_plugin_ratio'] * 100, 2);
						        out::H($hang_plugin_ratio);
						        echo "%";
					            }
				                    ?></strong></td>
					  <?php }//if in_array hang_plugin
                                                ?>




				<?php
 						$i++;
						}
					}
				?>
			</tr>

		</table>

	<?php } else { ?>

		<p>No data is available for this query.</p>

	<?php } ?>


    </div>

</div>
