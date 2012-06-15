
<p>Fill out the form below to reset your password.</p>

<form id="authForm" name="authForm" action="<?php echo html::specialchars($form_url); ?>" method="post">

	<?php echo form::hidden('token', $token); ?>

	<?php echo form::label('password', 'New Password'); ?>
	<?php echo form::password('password'); ?>

	<?php echo form::label('password_confirm', 'Confirm New Password'); ?>
	<?php echo form::password('password_confirm'); ?>

	<br /><br />

	<?php echo form::submit('action_reset_password', 'Reset Password');?>

</form>
