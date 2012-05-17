/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */


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
