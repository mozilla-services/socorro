<p>Use the form below to change your email address.  Your current email address is <strong><?php echo html::specialchars($current_email); ?></strong> .</p>

<form id="authForm" name="authForm" action="<?php echo html::specialchars($form_url); ?>" method="post">

	<?php echo form::label('email', 'New Email Address'); ?>
	<?php echo form::input('email'); ?>
	joe@example.com

	<?php echo form::label('email_confirm', 'Confirm New Email Address'); ?>
	<?php echo form::input('email_confirm'); ?>
	joe@example.com

	<br /><br />

	<?php echo form::submit('action_change_email', 'Change Email');?>

	<script type="text/javascript">document.getElementById('email').focus();</script>

</form>
