
<div id="crash_data">

	<h2>Crash Data</h2> <span class="csv"><a href="<?php echo $url_csv; ?>">download csv</a></span><br />
	
	<?php if (isset($results->versions) && isset($versions) && !empty($versions)) { ?>
		
		<table class="crash_data">
			<tr>
				<th class="date" rowspan="2">Date</th>
				<?php foreach ($versions as $key => $version) { ?>
					<?php if (!empty($version)) { ?>
						<th class="version<?php echo $key; ?>" colspan="3"><?php out::H($version); ?></th>
					<?php } ?>
				<?php } ?>
				</tr>
				<tr>
				<?php foreach ($versions as $version) { ?>
					<?php if (!empty($version)) { ?>
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
						$i = 0;
						foreach ($results->versions as $version) { 
							if ($version->version == $versions[$i]) {
								$key = $version->version;
					?>
					
								<td><?php 
									if (isset($statistics['versions'][$key][$date]['crashes'])) {
										out::H($statistics['versions'][$key][$date]['crashes']); 
									} else {
										echo '-';
									}
								?></td>
								<td><?php 
									if (isset($statistics['versions'][$key][$date]['users'])) {
										out::H($statistics['versions'][$key][$date]['users'] / 1000); 
									} else {
										echo '-';
									}
								?></td>	
								<td><?php 
									if (isset($statistics['versions'][$key][$date]['ratio'])) {
										$ratio = round($statistics['versions'][$key][$date]['ratio'] * 100, 3);
										out::H($ratio);
										echo "%";
									} else {
										echo '-';
									}
								?></td>							
					<?php			
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
					if (isset($statistics['versions'][$key]['crashes'])) {
						out::H($statistics['versions'][$key]['crashes']); 
					}
				?></strong></td>
				<td class="stat"><strong><?php 
					if (isset($statistics['versions'][$key]['users'])) {
						out::H($statistics['versions'][$key]['users'] / 1000); 
					}
				?></strong></td>	
				<td class="stat"><strong><?php 
					if (isset($statistics['versions'][$key]['ratio'])) {
						$ratio = round($statistics['versions'][$key]['ratio'] * 100, 3);
						out::H($ratio);
						echo "%"; 
					}
				?></strong></td>							

				
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
