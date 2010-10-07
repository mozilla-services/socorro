<h1>Email Subscription Status</h1>
<?php if ($backend_error) { ?>
     <p>Error: <strong>Our email system is down</strong>. Please try in a few minutes.</p>
<?php } elseif ($unknown_token) { ?>
     <p>Error: Unable to load <?= $token ?>. Are you sure we sent you this code?</p>
<?php } else { ?>
  <form action="../update_status" method="post">
    <label for="subscribe_status">You are currently 
       <input type="radio" name="subscribe_status" value="true"  <?php if ($status)   echo 'CHECKED' ?>   >Subscribed</input>
       <input type="radio" name="subscribe_status" value="false" <?php if (! $status) echo 'CHECKED' ?> >Not Subscribed</input>
    to crash report emails.</label>
    <input type="hidden" name="token" value="<?= out::H($token) ?>" />
      <h3>Word Verification</h3>
      <p>This question is for testing whether you are a human being!</p>
      <?php if ($recaptchaError) { ?>
        <div class='error'><?= $recaptchaError ?></div>
      <?php } else if ($success) {?>
        <div class='success'>Thanks, we've updated your email preferences.</div>
      <?php } ?>
<script type="text/javascript">
var RecaptchaOptions = {
   theme : 'white',
   lang : 'en'
};
</script>
    <?php echo recaptcha::html($recaptchaErrorCode, FALSE); ?>
    <input type="submit" name="submit" value="Update Email Subscription" />
  </form>
<?php } ?>