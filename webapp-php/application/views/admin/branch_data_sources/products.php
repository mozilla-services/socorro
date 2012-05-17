<?php if (isset($products) && !empty($products)) { ?>
	<?php foreach ($products as $product) { ?>
		<h4><?php echo html::specialchars($product); ?></h4>
		<table>
            <thead>
	    		<tr>
		    	<th>Product</th>
		    	<th>Version</th>
			    <th>Release</th>
			    <th>Start Date</th>
			    <th>End Date</th>
			    <th>Featured</th>
			    <th>Throttle</th>
			    </tr>
            </thead>
            <tbody>
			<?php foreach ($versions as $version) { ?>
				<?php if ($version->product == $product) { ?>
					<tr>
						<td class="text"><?php echo html::specialchars(html::specialchars($version->product)); ?></td>
						<td class="text"><?php echo html::specialchars(html::specialchars($version->version)); ?></td>
						<td class="text"><?php echo html::specialchars(html::specialchars($version->release)); ?></td>
						<td class="date"><?php
							if (isset($version->start_date)) {
								echo html::specialchars(str_replace('00:00:00', '', $version->start_date));
							}
						?></td>
						<td class="date"><?php
							if (isset($version->end_date)) {
								echo html::specialchars(str_replace('00:00:00', '', $version->end_date));
							}
						?></td>
						<td class="featured"><?php
						    if (isset($version->featured) && $version->featured == 't') {
						        echo '&#10004;';
						    }
						?></td>
						<td class="throttle"><?php
						    if (isset($version->throttle) && $version->throttle > 0) {
						        out::H($version->throttle);
						    } else {
						        echo '-.--';
						    }
						?>%</td>
					</tr>
				<?php } ?>
			<?php } ?>
            </tbody>
		</table>
	<?php } ?>
<?php } ?>