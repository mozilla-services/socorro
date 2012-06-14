/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */


<p>Enter your email address below, and if we can find an account that matches your email address, we'll send you a link to reset your password.</p>

<form id="authForm" name="authForm" action="<?php echo html::specialchars($form_url); ?>" method="post">

	<?php echo form::hidden('token', $_SESSION['token'] = uniqid()); ?>

	<?php echo form::label('email', 'Email Address'); ?>
	<?php echo form::input('email'); ?>
	joe@example.com

	<br /><br />

	<?php echo form::submit('action_send_link', 'Send Link');?>

	<script type="text/javascript">document.getElementById('email').focus();</script>

</form>
