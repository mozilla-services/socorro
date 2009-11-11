	<div id="comments">
		<h2>Comments</h2>
		<?php if (!empty($comments)) { ?>
			<?php foreach ($comments as $comment) { ?>
				<p class="crash_comments"><?php echo nl2br(out::h($comment->user_comments)); ?></p>
				<p class="crash_comments">Submitted: <?php out::h($comment->client_crash_date); ?></p>
				<?php if ($logged_in) { ?> 
					<p class="crash_comments">Email: <a href="mailto:<?php out::h($comment->email); ?>"><?php out::h($comment->email); ?></a></p>
				<?php } ?>
				<hr>
			<?php } ?>
		<?php } else { ?>
			<p><em>No comments are available.</p>
		<?php } ?>
    </div>