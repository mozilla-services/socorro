
<div id="daily_search">
    <h2>Select a Report</h2>

    <div id="daily_search_version">
        <h3><a href="#" id="click_by_version">Crashes per ADU by Version</a></h3>
        <form id="daily_search_version_form" action="<?php out::H($url_form); ?>" method="get" <?php if ($form_selection != 'by_version') echo 'style="display: none"'; ?>>

			<input type="hidden" name="form_selection" value="by_version">

			<table class="by_version">
				<tr>
				<th>Product</th>
				<td>
				<select name="p">
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
					<th>Versions</th> 	
					<td>
					<input class="version" type="text" name="v[]" value="<?php if (!empty($versions[0])) out::H($versions[0]); ?>" />
					<input class="version" type="text" name="v[]" value="<?php if (!empty($versions[1])) out::H($versions[1]); ?>" />
					<input class="version" type="text" name="v[]" value="<?php if (!empty($versions[2])) out::H($versions[2]); ?>" />
					<input class="version" type="text" name="v[]" value="<?php if (!empty($versions[3])) out::H($versions[3]); ?>" />								
					</td>
				</tr>
				
				<tr>
					<th>O/S</th> 	
					<td>
						<?php foreach ($operating_systems as $os) { ?>
							<input type="checkbox" name="os[]" value="<?php out::H($os); ?>" 
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

			<input type="submit" name="submit" value="Generate">
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
				<select name="p">
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
					<td><input class="version" type="text" name="v[]" value="<?php if (!empty($versions)) out::H(array_shift($versions)); ?>" /></td>
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
