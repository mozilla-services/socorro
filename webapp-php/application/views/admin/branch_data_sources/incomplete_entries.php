<?php if (isset($missing_visibility_entries) && !empty($missing_visibility_entries)) { ?>
	<p>The following entries appear in the productdims table but do not have corresponding entries in the product_visibility table.</p>
	<table class="branch">
        <thead>
		    <tr>
		    <th>Product</th>
		    <th>Version</th>
	    	<th># Records</th>
		    <th>Add?</th>
		    </tr>
        </thead>
        <tbody>
	    <?php foreach ($missing_visibility_entries as $missing_entry) { ?>
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
        </tbody>
	    </table>
<?php } else { ?>
	<p>All entries in the productdims table have corresponding entries in the product_visibility table.</p>
<?php } ?>