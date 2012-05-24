/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

	<div id="comments" class="ui-tabs-hide">
	     <h2>Comments</h2>
		<?php if (!empty($comments)) { ?>
			<?php foreach ($comments as $comment) { ?>
				<p class="crash_comments"><?php echo nl2br(out::h($comment->user_comments)); ?></p>
				<p class="crash_comments"><a href="<?= url::site('report/index/' . $comment->uuid)?>">Submitted: <?php out::h($comment->date_processed); ?></a></p>
				<?php if ($logged_in) { ?>
					<p class="crash_comments">Email: <a href="mailto:<?php out::h($comment->email); ?>"><?php out::h($comment->email); ?></a></p>
				<?php } ?>
				<hr>
			<?php } ?>
		<?php } else { ?>
			<p><em>No comments are available.</p>
		<?php } ?>
    </div>
