<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>

<div class="panel daily_">
	<div class="title">
		<h2>Crashes per ADU</h2>
		<div class="choices">
			<ul>
				<li><a href="<?php echo $url_csv; ?>">csv</a></li>
			</ul>
		</div>
    </div>

    <div class="body">

	<?php if ((isset($versions_in_result) && !empty($versions_in_result)) && (isset($versions) && !empty($versions))) { ?>

		<table id="crash_data" class="data-table crash_data zebra">
			<tr>
				<th class="date" rowspan="2">Date</th>
				<?php foreach ($versions_in_result as $key => $version) { ?>
					<?php if (!empty($version)) { ?>
						<th class="version" colspan="4"><?php out::H($version); ?></th>
					<?php } ?>
				<?php } ?>
				</tr>
				<tr>
				<?php foreach ($versions_in_result as $version) { ?>
					<?php if (!empty($version)) { ?>
						<th class="stat">Crashes</th>
						<th class="stat">ADU</th>
						<th class="stat" title="The throttle rate is the effective throttle rate - the combined throttle rate for client-side throttling and server-side throttling.">Throttle</th>
						<th class="stat">Ratio</th>
					<?php } ?>
				<?php } ?>
			</tr>

			<?php foreach ($dates as $date) { ?>
				<tr>
					<td><?php out::H($date); ?></td>

					<?php
                        for ($i = 0; count($versions_in_result) > $i; $i++) {
                            $key = $versions_in_result[$i];
					?>

								<td><?php
									if (isset($statistics['versions'][$key][$date]['crashes'])) {
										out::H(number_format(round($statistics['versions'][$key][$date]['crashes'])));
									} else {
										echo '-';
									}
								?></td>
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
								<td><?php
									if (isset($statistics['versions'][$key][$date]['ratio'])) {
										$ratio = $statistics['versions'][$key][$date]['ratio'];
										out::H($ratio);
										echo "%";
									} else {
										echo '-';
									}
								?></td>
					<?php
						}
					?>
				</tr>
			<?php } ?>

			<tr>
				<td class="date"><strong>Total</strong></td>
			<?php
                for ($i = 0; count($versions_in_result) > $i; $i++) {
                    $key = $versions_in_result[$i];
			?>
				<td class="stat"><strong><?php
					if (isset($statistics['versions'][$key]['crashes'])) {
						out::H(number_format(round($statistics['versions'][$key]['crashes'])));
					}
				?></strong></td>
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
				<td class="stat"><strong><?php
					if (isset($statistics['versions'][$key]['ratio'])) {
						$ratio = $statistics['versions'][$key]['ratio'];
						out::H($ratio);
						echo "%";
					}
				?></strong></td>


				<?php
					}
				?>
			</tr>

		</table>

	<?php } else { ?>

		<p>No data is available for this query.</p>

	<?php } ?>


    </div>

</div>
