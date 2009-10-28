
Use the form below to change your password.

<form id="authForm" name="authForm" action="<?php echo html::specialchars($form_url); ?>" method="post">

	<?php // echo form::label('password_current', 'Current Password'); ?>
	<?php // echo form::password('password_current'); ?> 

	<?php echo form::label('password', 'New Password'); ?>
	<?php echo form::password('password'); ?> 

	<?php echo form::label('password_confirm', 'Confirm New Password'); ?>
	<?php echo form::password('password_confirm'); ?> 

	<br /><br />
	
	<?php echo form::submit('action_change_password', 'Change Password');?>

</form>

<script type="text/javascript">document.getElementById('password').focus();</script>