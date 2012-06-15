
<form id="authForm" name="authForm" action="<?php echo html::specialchars($form_url); ?>" method="post">

	<?php echo form::hidden('token', $_SESSION['token'] = uniqid()); ?>

	<?php echo form::label('username', 'User Name'); ?>
	<?php echo form::input('username', $username); ?>
	Must be at least 4 characters in length

	<?php echo form::label('email', 'Email Address'); ?>
	<?php echo form::input('email', $email); ?>
	john@example.com

	<?php echo form::label('email_confirm', 'Confirm your Email Address'); ?>
	<?php echo form::input('email_confirm', $email_confirm); ?>
	john@example.com

	<?php echo form::label('password', 'Password'); ?>
	<?php echo form::password('password', $password); ?>
	Must be at least 6 characters in length

	<?php echo form::label('password_confirm', 'Confirm your Password'); ?>
	<?php echo form::password('password_confirm', $password_confirm); ?>

	<?php echo form::label('captcha_response', 'Enter the Pictured Text')?>
	<?php echo form::input('captcha_response'); ?> <br />
	<?php echo Captcha::instance()->render(); ?>

	<br /><br />

	<?php echo form::submit('action_create', 'Create Account');?>

	<p>By clicking Create Account, you confirm that you accept the <a href="/terms">Terms of Use</a>.</p>

	<p>Already have an account?  <a href="/login">Login</a>.</p>

</form>

<script type="text/javascript">document.getElementById('username').focus();</script>
