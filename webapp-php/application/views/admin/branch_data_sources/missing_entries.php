<?php if (isset($missing_entries) && !empty($missing_entries)) { ?>
	<p>The following are entries that appear in the reports but are not present in the `branches` table.</p>
	<table class="branch">
        <thead>
		    <tr>
		    <th>Product</th>
		    <th>Version</th>
		    <th># Records</th>
		    <th>Add?<span>&nbsp;</span></th>
		    </tr>
         </thead>
         <tbody>
	     <?php foreach ($missing_entries as $missing_entry) { ?>
		    <tr>
			    <td class="text"><?php echo html::specialchars($missing_entry->product); ?></td>
		    	<td class="text"><?php echo html::specialchars($missing_entry->version); ?></td>
			    <td class="text"><?php if (isset($missing_entry->total)) echo html::specialchars($missing_entry->total); ?></td>
			    <td class="action"><a href="#form_add_version" onclick="branchAddProductVersionFill(
				    '<?php echo trim(html::specialchars($missing_entry->product)); ?>',
				    '<?php echo trim(html::specialchars($missing_entry->version)); ?>'
			    ); return false;">add</a></td>
		     </tr>
	     <?php } ?>
         </tbody>
	</table>
<?php } else { ?>
	<p>All entries in the reports are accounted for in the `branches` table.</p>
<?php } ?>