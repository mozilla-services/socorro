/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */


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
