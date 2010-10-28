<div class="page-heading">
  <h2>Post Crash Email</h2>
</div>
<div class="panel postcrash">
  <?php View::factory('common/recent_email_campaigns')->render(TRUE); ?>
  <div class="body notitle">
    <div class="admin">
      <h3>Confirm Email</h3>
      <?php View::factory('common/form_errors')->render(TRUE); ?>

      <?php if (isset($estimated_count)) { ?>
        <p>Sending this email <strong>will contact <?= $estimated_count ?></strong> 
         <?= $email_product?> <?= $email_versions ?> users who crashed on <?= out::H($email_signature) ?> 
           between <?= $email_start_date ?> and <?= $email_end_date ?></p>
         <div><p><strong>Subject:</strong><pre><?= out::H($email_subject) ?></pre></p>
         <p><strong>Email Body:</strong><pre><?= out::H($email_body)?></pre></p></div>
        <p>Note: Email template variables are displayed above, don't worry they will be
            replaced in the actual email.</p>
        <p>Note: The number of contacts above is an estimate. We won't email
           a user who has already been contacted about <?= $email_product ?>'s 
           <?= out::H($email_signature) ?> crash. Malformed email addresses may also inflate the estimate.
           The estimate is higher or the same as
           the actual number of email addresses that will be contacted, if you choose to continue.</p>
        <form class="" name="postcrashemail" action="send_email" method="post">

          <input type="hidden" name="email_product"    value="<?= $email_product ?>" />
          <input type="hidden" name="email_versions"   value="<?= $email_versions ?>" />
          <input type="hidden" name="email_signature"  value="<?= out::H($email_signature) ?>" />
          <input type="hidden" name="email_subject"    value="<?= out::H($email_subject) ?>" />
          <input type="hidden" name="email_body"       value="<?= out::H($email_body) ?>" />
          <input type="hidden" name="email_start_date" value="<?= $email_start_date ?>" />
          <input type="hidden" name="email_end_date"   value="<?= $email_end_date ?>" />

          <input name="submit" type="submit" value="OK, Send Emails" />   
          <input name="submit" type="submit" value="Cancel" />
        </form>
      <?php } ?>
      <br class="clear" />
    </div><!-- .admin -->
  </div><!-- .body .notitle -->
</div><!-- .panel -->
