<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>

<div class="panel daily_search">
	<div class="title daily_search_title">
        <h2>Select a Report</h2>
    </div>

    <div class="body daily_search_body">
        <div id="daily_search">
        <div id="daily_search_version">
            <h3><a href="#" id="click_by_version">Crashes per ADU by Version</a></h3>
            <p>All ADU ratios are generated per 100 ADUs, not per single ADU. "3.5 crashes/ADU" means that there are 3.5 crashes per 100 users, not per user. This ratio also does not distinguish between users who crash multiple times and multiple crashing users.</p>
            <form id="daily_search_version_form" name="daily_search_version_form" action="<?php out::H($url_form); ?>" method="get" <?php if ($form_selection != 'by_version') echo 'style="display: none"'; ?>>

	    		<input type="hidden" name="form_selection" value="by_version">

	    		<table class="by_version">
                    <tr>
                    <th>Product</th>
                    <td>
                    <select id="daily_search_version_form_products" name="p">
                        <?php View::factory('common/products_select', array('products' => $products))->render(TRUE); ?>
                    </select>
                    </td>
                    </tr>

	    			<tr>
	    				<th rowspan="4" valign="top">Versions</th>
                        <?php for($key=0; $key<=3; $key++) {
                            if ($key != 0) echo '<tr>';
                        ?>

                        <td><select id="version<?php echo $key; ?>" name="v[]">
                                <option value="">-- versions --</option>
                                <?php foreach ($product_versions as $product_version) { ?>
                                    <option value="<?php echo $product_version->version; ?>" throttle="<?php echo $product_version->throttle; ?>" key="<?php echo $key; ?>"
                                        <?php if (isset($versions[$key]) && $product_version->version == $versions[$key]) echo 'SELECTED'; ?>
                                    ><?php echo $product_version->version; ?></option>
                                <?php } ?>
                            </select>
                        </td>
                        </tr>
                        <?php } ?>
                    </tr>


	    			<tr>
				        <th>Type:</th>
	    				<td>
                            <span class="radio-item"><label><?= form::radio('hang_type', 'any',   $hang_type == ''); ?> Any</label></span>
                            <span class="radio-item"><label><?= form::radio('hang_type', 'crash', $hang_type == 'crash'); ?> Crash</label></span>
                            <span class="radio-item"><label><?= form::radio('hang_type', 'hang-p',  $hang_type == 'hang-p'); ?> Plugin Hang</label></span>
	    				</td>
	    			</tr>
	    			<tr>
	    				<th>O/S</th>
	    				<td>
	    					<?php foreach ($operating_systems as $os) { ?>
	    						<input id="os_<?=$os?>_check" type="checkbox" name="os[]" value="<?php out::H($os); ?>"
	    							<?php if (in_array($os, $operating_system)) { ?>
	    								CHECKED
	    							<?php } ?>
	    						/> <?php out::H($os); ?> &nbsp;&nbsp;
	    					<?php } ?>
	    				</td>
	    			</tr>

                    <tr>
                        <?php 
                            $by_build = ($date_range_type == 'build' ? TRUE : FALSE); 
                        ?>
                        <td>Date Range</td>
                        <td>
                            <span class="radio-item">
                                <label for="by_build">
                                    <input type="radio" name="date_range_type" id="by_build" value="build"
                                    <?php 
                                        if ($by_build) {
                                            echo 'checked="checked"'; 
                                        }
                                    ?> /> Build Date
                                </label>
                            </span>
                            <span class="radio-item">
                                <label for="crash">
                                    <input type="radio" name="date_range_type" id="crash" value="report"
                                    <?php 
                                        if (!$by_build) {
                                            echo 'checked="checked"'; 
                                        }
                                    ?> /> Crash Date
                                </label>
                            </span>
                    </tr>

	    			<tr class="datepicker-daily">
	    				<th>When</th>
	    				<td>
	    				<input class="date" type="text" name="date_start" value="<?php out::H($date_start); ?>" />
	    				&nbsp; to &nbsp;
	    				<input class="date" type="text" name="date_end" value="<?php out::H($date_end); ?>" />
	    				</td>
	    			</tr>
	    		</table>

	    		<input id="daily_search_version_form_submit" type="submit" name="submit" value="Generate">
	    	</form>
	    </div>

	    <div id="daily_search_os">
	    	<h3><a href="#" id="click_by_os">Crashes per ADU by O/S</a></h3>
	    	<form id="daily_search_os_form" action="<?php out::H($url_form); ?>" method="get" <?php if ($form_selection != 'by_os') echo 'style="display: none"'; ?>>
	    		<input type="hidden" name="form_selection" value="by_os">

	    		<table class="by_version">
	    			<tr>
	    			<th>Product</th>
	    			<td>
	    			<select id="daily_search_os_form_products" name="p">
	    				<?php foreach ($products as $p) { ?>
	    					<option value="<?php out::H($p); ?>"
	    						<?php if ($p == $product) { ?>
	    							SELECTED
	    						<?php } ?>
	    					><?php out::H($p); ?></option>
	    				<?php } ?>
	    			</select>
	    			</td>
	    			</tr>

	    			<tr>
	    				<th>Version</th>
	    				<td>
	    				    <?php $selected_version = (isset($versions[0]) && !empty($versions[0])) ? $versions[0] : ''; ?>
	    				    <select id="version4" name="v[]">
                                <option value="">-- versions --</option>
                                <?php foreach ($product_versions as $product_version) { ?>
                                    <option value="<?php echo $product_version->version; ?>" throttle="<?php echo $product_version->throttle; ?>" key="<?php echo $key; ?>"
                                        <?php if ($product_version->version == $selected_version) echo 'SELECTED'; ?>
                                    ><?php echo $product_version->version; ?></option>
                                <?php } ?>
                            </select>
                        </td>
	    			</tr>

	    			<tr>
                    <th>Type:</th>
	    				<td>
                           <span class="radio-item"><label><?= form::radio('hang_type', 'any',   $hang_type == ''); ?> Any</label></span>
                           <span class="radio-item"><label><?= form::radio('hang_type', 'crash', $hang_type == 'crash'); ?> Crash</label></span>
                           <span class="radio-item"><label><?= form::radio('hang_type', 'hang-p',  $hang_type == 'hang-p'); ?> Plugin Hang</label></span>
	    				</td>
	    			</tr>

                    <tr>
                        <?php 
                            $by_build = ($date_range_type == 'build' ? TRUE : FALSE); 
                        ?>
                        <td>Date Range</td>
                        <td>
                            <span class="radio-item">
                                <label for="os_by_build">
                                    <input type="radio" name="date_range_type" id="os_by_build" value="build"
                                    <?php 
                                        if ($by_build) {
                                            echo 'checked="checked"'; 
                                        }
                                    ?> /> Build Date
                                </label>
                            </span>
                            <span class="radio-item">
                                <label for="os_crash">
                                    <input type="radio" name="date_range_type" id="os_crash" value="report"
                                    <?php 
                                        if (!$by_build) {
                                            echo 'checked="checked"'; 
                                        }
                                    ?> /> Crash Date
                                </label>
                            </span>
                    </tr>

	    			<tr class="datepicker-daily">
	    				<th>When</th>
	    				<td>
	    				<input class="date" type="text" name="date_start" value="<?php out::H($date_start); ?>" />
	    				&nbsp; to &nbsp;
	    				<input class="date" type="text" name="date_end" value="<?php out::H($date_end); ?>" />
	    				</td>
	    			</tr>
	    		</table>

	    		<input type="submit" name="submit" value="Generate">
	    	</form>
	    </div>

        </div>
    </div>

</div>
