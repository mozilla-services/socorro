
<div class="page-heading">
	<h2>Branch Data Sources</h2>
</div>


<div class="panel">
    <div class="body notitle">

<div class="admin">
	<p>Manage thy branch data sources here.  Information about maintaining this data can be found in the <a href="https://wiki.mozilla.org/Socorro/SocorroUI/Branches_Admin">Socorro</a> wiki.</p>
	
	<h3>Missing Entries</h3>
	<?php if (isset($missing_entries) && !empty($missing_entries)) { ?>
		<p>The following are entries that appear in the reports but are not present in the `branches` table.</p>
		<table class="branch">
			<tr>
			<th>Product</th>
			<th>Version</th>
			<th># Records</th>
			<th>Add?</th>
			</tr>
		<?php foreach ($missing_entries as $missing_entry) { ?>
			<tr>
				<td class="text"><?php echo html::specialchars($missing_entry->product); ?></td>
				<td class="text"><?php echo html::specialchars($missing_entry->version); ?></td>
				<td class="text"><?php if (isset($missing_entry->total)) echo html::specialchars($missing_entry->total); ?></td>
				<td class="action"><a href="#form_add_version" onclick="branchAddProductVersionFill(
					'<?php echo trim(html::specialchars($missing_entry->product)); ?>', 
					'<?php echo trim(html::specialchars($missing_entry->version)); ?>'
				);">add</a></td>
			</tr>
		<?php } ?>
		</table>
	<?php } else { ?>
		<p>All entries in the reports are accounted for in the `branches` table.</p>
	<?php } ?>
	
	<h3>Incomplete Entries</h3>
	<?php if (isset($missing_entries) && !empty($missing_entries)) { ?>
		<p>The following entries appear in the productdims table but do not have corresponding entries in the product_visibility table.</p>
		<table class="branch">
			<tr>
			<th>Product</th>
			<th>Version</th>
			<th># Records</th>
			<th>Add?</th>
			</tr>
		<?php foreach ($missing_visibility_entries as $missing_entry) { ?>
			<tr>
				<td class="text"><?php echo html::specialchars($missing_entry->product); ?></td>
				<td class="text"><?php echo html::specialchars($missing_entry->version); ?></td>
				<td class="text"><?php if (isset($missing_entry->total)) echo html::specialchars($missing_entry->total); ?></td>
				<td class="action"><a href="#form_add_version" onclick="branchAddProductVersionFill(
					'<?php echo trim(html::specialchars($missing_entry->product)); ?>', 
					'<?php echo trim(html::specialchars($missing_entry->version)); ?>'
				);">add</a></td>
				<td class="action"><a href="#delete_product_version" onclick="branchDeleteProductVersionFill(
					'<?php echo trim(html::specialchars($missing_entry->product)); ?>',
					'<?php echo trim(html::specialchars($missing_entry->version)); ?>'
				);">delete</a></td>
			</tr>
		<?php } ?>
		</table>
	<?php } else { ?>
		<p>All entries in the productdims table have corresponding entries in the product_visibility table.</p>
	<?php } ?>


	<h3>Products</h3>
	
	<span><a href="#" onclick="branchAddProductVersion(); return false;">add new product version</a></span>
	<div id="add_version" name="add_version" class="add_item" style="display: none;">
		<p>Fill out this form to add a new product version.</p>
		<form action="" id="form_add_version" name="form_add_version" method="post">
			<input type="hidden" name="action_add_version" value="1">

			<table>
			<tr><td>Product: </td><td><input type="text" id="product" name="product" value="" /></p>
			<tr><td>Version: </td><td><input type="text" id="version" name="version" value="" /></p>
			<tr><td>Branch: </td><td> 
			<select name="branch">
			<?php foreach ($branches as $branch) { ?>
				<option value="<?php echo html::specialchars($branch->branch); ?>"><?php echo html::specialchars($branch->branch); ?></option>
			<?php } ?>
			</select>
			</td></tr>
			<tr><td>Start Date: </td><td><input class="text" type="text" id="start_date" name="start_date" value="<?php echo html::specialchars($default_start_date); ?>" /></td></tr>
			<tr><td>End Date:</td><td><input class="text" type="text" id="end_date" name="end_date" value="<?php echo html::specialchars($default_end_date); ?>" /></td></tr>
            <tr><td>Featured:   </td><td><input type="checkbox" id="featured" name="featured" value="t" /></td></tr>
            <tr><td>Throttle:   </td><td><input class="text" type="text" id="throttle" name="throttle" value="<?php echo $throttle_default; ?>" />% [<a href="http://code.google.com/p/socorro/wiki/SocorroUIAdmin#Throttle" target="_NEW">?</a>]</td></tr>
			</table>
			<p id="add_submit"><input type="submit" name="submit" value="Add Product Version" onclick="hideShow('add_submit', 'add_submit_progress');" /></p>
			<p id="add_submit_progress" style="display:none;"><img src="<?php echo url::site(); ?>img/loading.png" /> <em>please wait...</em></p>
		</form>
	</div>
	
	<div id="update_product_version" name="update_product_version" class="add_item" style="display: none;">
		<p>Fill out this form to update an existing product version.</p>
		<form action="" id="form_update_version" name="form_update_version" method="post">
			<input type="hidden" name="action_update_version" value="1">

			<table>
			<tr><td>Product: </td>
				<td>
					<input type="hidden" id="update_product" name="update_product" value="" />
					<span id="update_product_display" name="update_product_display"></span>
				</td>
			</tr>
			<tr><td>Version: </td>
				<td>
					<input type="hidden" id="update_version" name="update_version" value="" />
					<span id="update_version_display" name="update_version_display"></span>
				</td>
			</tr>
			<tr><td>Branch:  	</td><td><input class="text" type="text" id="update_branch" name="update_branch" value="" /></td></tr>
			<tr><td>Start Date: </td><td><input class="text" type="text" id="update_start_date" name="update_start_date" value="" /></td></tr>
			<tr><td>End Date: 	</td><td><input class="text" type="text" id="update_end_date" name="update_end_date" value="" /></td></tr>
            <tr><td>Featured:   </td><td><input type="checkbox" id="update_featured" name="update_featured" value="t" /></td></tr>
            <tr><td>Throttle:   </td><td><input class="text" type="text" id="update_throttle" name="update_throttle" value="<?php echo $throttle_default; ?>" />% [<a href="https://wiki.mozilla.org/Socorro/SocorroUI/Branches_Admin#Throttle" target="_NEW">?</a>]</td></tr>
			</table>

			<p id="update_submit"><input type="submit" name="submit" value="Update Product Version" onclick="hideShow('update_submit', 'update_submit_progress');" /></p>
			<p id="update_submit_progress" style="display:none;"><img src="<?php echo url::site(); ?>img/loading.png" /> <em>please wait...</em></p>
		</form>
	</div>
	
	
	<div id="delete_product_version" name="delete_product_version" class="add_item" style="display: none;">
		<p>Do you really want to delete this product version?</p>
		<form action="" id="form_delete_version" name="form_delete_version" method="post">
			<input type="hidden" name="action_delete_version" value="1">

			<span class="push_right">
			Product: 
				<input type="hidden" id="delete_product" name="delete_product" value="" />
				<span id="delete_product_display" name="delete_product_display"></span>
			</span>

			<span class="push_right">
			Version:
				<input type="hidden" id="delete_version" name="delete_version" value="" />
				<span id="delete_version_display" name="delete_version_display"></span>
			</span>

			<p id="delete_submit"><input type="submit" name="submit" value="Yes, I want to Delete this Product Version" onclick="hideShow('delete_submit', 'delete_submit_progress');" /></p>
			<p id="delete_submit_progress" style="display:none;"><img src="<?php echo url::site(); ?>img/loading.png" /> <em>please wait...</em></p>
		</form>
	</div>
	
	<?php if (isset($products) && !empty($products)) { ?>
		<?php foreach ($products as $product) { ?>
			<h4><?php echo html::specialchars($product); ?></h4>
			<table>
				<tr>
				<th>Product</th>
				<th>Version</th>
				<th>Branch</th>
				<th>Release</th>
				<th>Start Date</th>
				<th>End Date</th>
				<th>Featured</th>
				<th>Throttle</th>
				<th>Update?</th>
				<th>Delete?</th>
				</tr>

				<?php foreach ($versions as $version) { ?>
					<?php if ($version->product == $product) { ?>
						<tr>
							<td class="text"><?php echo html::specialchars(html::specialchars($version->product)); ?></td>
							<td class="text"><?php echo html::specialchars(html::specialchars($version->version)); ?></td>
							<td class="date"><?php echo html::specialchars(html::specialchars($version->branch)); ?></td>
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
							<td class="action"><a href="#update_product_version" onclick="branchUpdateProductVersionFill(
								'<?php echo trim(html::specialchars($version->product)); ?>',
								'<?php echo trim(html::specialchars($version->version)); ?>',
								'<?php echo trim(html::specialchars($version->branch)); ?>',
								'<?php if (isset($version->start_date)) echo html::specialchars(str_replace('00:00:00', '', $version->start_date)); else echo ''; ?>',
								'<?php if (isset($version->end_date)) echo html::specialchars(str_replace('00:00:00', '', $version->end_date)); else echo ''; ?>',
								'<?php if (isset($version->featured) && $version->featured == 't') echo 't'; else echo 'f'; ?>',
    							'<?php if (isset($version->throttle) && $version->throttle > 0) out::H($version->throttle); else echo $throttle_default; ?>'
							);">update</a></td>
							<td class="action"><a href="#delete_product_version" onclick="branchDeleteProductVersionFill(
								'<?php echo trim(html::specialchars($version->product)); ?>',
								'<?php echo trim(html::specialchars($version->version)); ?>'
							);">delete</a></td>							
						</tr>
					<?php } ?>
				<?php } ?>
			</table>
		<?php } ?>
	<?php } ?>
	

</div>

    </div>
</div>
