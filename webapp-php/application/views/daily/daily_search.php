
<div class="panel daily_search">
	<div class="title daily_search_title">
        <h2>Select a Report</h2>
    </div>

    <div class="body daily_search_body">
        <div id="daily_search">
        <div id="daily_search_version">
            <h3><a href="#" id="click_by_version">Crashes per ADU by Version</a></h3>
            <form id="daily_search_version_form" name="daily_search_version_form" action="<?php out::H($url_form); ?>" method="get" <?php if ($form_selection != 'by_version') echo 'style="display: none"'; ?>>
        
	    		<input type="hidden" name="form_selection" value="by_version">
        
	    		<table class="by_version">
                    <tr>
                    <th>Product</th>
                    <td>
                    <select id="daily_search_version_form_products" name="p">
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
                            </select> throttle <input id="throttle<?php echo $key; ?>" class="version" type="text" name="throttle[]" value="<?php if (isset($throttle[$key]) && !empty($throttle[$key])) out::H($throttle[$key]); else echo $throttle_default; ?>"  title="The throttle rate is the effective throttle rate - the combined throttle rate for client-side throttling and server-side throttling." />%</td>
                        </td>
                        </tr>
                        <?php } ?>

	    			
	    			<tr>
				<th>Type:</th> 	
	    				<td>
                                            <span class="radio-item"><label><?= form::radio('hang_type', 'any',   $hang_type == 'any'); ?>
		    Any</label></span>
                                	    <span class="radio-item"><label><?= form::radio('hang_type', 'crash', $hang_type == 'crash'); ?>
		    Crash</label></span>
                                	    <span class="radio-item"><label><?= form::radio('hang_type', 'hang',  $hang_type == 'hang'); ?>
		    Hang</label></span>	    					
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
	    				    <?php $selected_version = (!empty($versions)) ? array_shift($versions) : ''; ?>
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
<th>Type:</th> 	
	    				<td>
                                            <span class="radio-item"><label><?= form::radio('hang_type', 'any',   $hang_type == 'any'); ?>
		    Any</label></span>
                                	    <span class="radio-item"><label><?= form::radio('hang_type', 'crash', $hang_type == 'crash'); ?>
		    Crash</label></span>
                                	    <span class="radio-item"><label><?= form::radio('hang_type', 'hang',  $hang_type == 'hang'); ?>
		    Hang</label></span>	    					
	    				</td>
	    			</tr>
	    			<tr>
	    				<th>Throttle</th> 	
	    				<td><input id="throttle4" class="version" type="text" name="throttle[]" value="<?php if (!empty($throttle)) out::H(array_shift($throttle)); ?>" title="The throttle rate is the effective throttle rate - the combined throttle rate for client-side throttling and server-side throttling." />%</td>
	    			</tr>
        
	    			<tr>
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
