/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<?php if (isset($products) && !empty($products)
    && isset($non_current_versions) && !empty($non_current_versions)) { ?>
    <p>The following entries are out of date and ineligible to be featured.</p>
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
		            <th>Throttle</th>
		        </tr>
            </thead>
            <tbody>
		    <?php foreach ($non_current_versions as $version) { ?>
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
 <?php } else { ?>
     <p>All entries in the reports are accounted for in current versions</p>
 <?php } ?>