
<div id="crash_data">

	<h2>Crash Data</h2> <span class="csv"><a href="<?php echo $url_csv; ?>">download csv</a></span><br />
	
	<?php if (isset($results->versions) && isset($versions) && !empty($versions)) { ?>
		
		<table class="crash_data">
			<tr>
				<th class="date" rowspan="2">Date</th>
				<?php foreach ($operating_systems as $key => $os) { ?>
					<?php if (!empty($os)) { ?>
						<th class="os<?php echo $key; ?>" colspan="3"><?php out::H($os); ?></th>
					<?php } ?>
				<?php } ?>
				</tr>
				<tr>
				<?php foreach ($operating_systems as $os) { ?>
					<?php if (!empty($os)) { ?>
						<th class="stat">Crashes</th>
						<th class="stat">1k ADU</th>
						<th class="stat">Ratio</th>
					<?php } ?>
				<?php } ?>
			</tr>

			<?php foreach ($dates as $date) { ?>
				<tr>
					<td><?php out::H($date); ?></td>

					<?php 
						foreach ($operating_systems as $os) { 
					?>
					
								<td><?php 
									if (isset($statistics['os'][$os][$date]['crashes'])) {
										out::H($statistics['os'][$os][$date]['crashes']); 
									} else {
										echo '-';
									}
								?></td>
								<td><?php 
									if (isset($statistics['os'][$os][$date]['users'])) {
										out::H($statistics['os'][$os][$date]['users'] / 1000); 
									} else {
										echo '-';
									}
								?></td>	
								<td><?php 
									if (isset($statistics['os'][$os][$date]['ratio'])) {
										$ratio = round($statistics['os'][$os][$date]['ratio'] * 100, 3);
										if ($ratio == 0.000 && $statistics['os'][$os][$date]['crashes'] > 0) {
											echo '0.001';
										} elseif ($ratio == 0) {
											echo '0.000';
										} else {
											out::H($ratio);
										}
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
				foreach($operating_systems as $os) { 
			?>
				<td class="stat"><strong><?php 
					if (isset($statistics['os'][$os]['crashes'])) {
						out::H($statistics['os'][$os]['crashes']); 
					}
				?></strong></td>
				<td class="stat"><strong><?php 
					if (isset($statistics['os'][$os]['users'])) {
						out::H($statistics['os'][$os]['users'] / 1000); 
					}
				?></strong></td>	
				<td class="stat"><strong><?php 
					if (isset($statistics['os'][$os]['ratio'])) {
						$ratio = round($statistics['os'][$os]['ratio'] * 100, 3);
						if ($ratio == 0.000 && $statistics['os'][$os]['crashes'] > 0) {
							echo '0.001';
						} elseif ($ratio == 0) {
							echo '0.000';
						} else {
							out::H($ratio);
						}
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