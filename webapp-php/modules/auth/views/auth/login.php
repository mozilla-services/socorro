
<form id="authForm" name="authForm" action="<?php echo html::specialchars($form_url); ?>" method="post">

	<?php echo form::hidden('token', $_SESSION['token'] = uniqid()); ?>

	<?php echo form::label('username', 'User Name'); ?>
	<?php echo form::input('username', $username); ?>

	<?php echo form::label('password', 'Password'); ?>
	<?php echo form::password('password', $password); ?>

	<?php // echo form::label('remember', 'Remember Me'); ?>
	<?php // echo form::checkbox('remember', $remember); ?>

	<br /><br />

	<?php echo form::submit('action_login', 'Login');?>

	<br /><br />

	<p>Can't remember your password?  Maybe we <a href="/forgot">can help</a>?</p>
	<p>Don't have an account?  <a href="/register">Register</a> now!</p>

</form>

<script type="text/javascript">document.getElementById('username').focus();</script>
