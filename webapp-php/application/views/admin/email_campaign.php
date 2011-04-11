<?php if (isset($campaign)) { ?>
  <h1>PostCrash Email Campaign</h2>
  <h2><?= out::h($campaign->product) ?> <?= out::h($campaign->versions) ?></h2>
  <p>Email campaign status: <?= out::h($campaign->status)?></p>
  <p>Email sent: <?= out::h($campaign->email_count)?></p>
  <p>Email status: <?= out::JSON($counts)?></p>
  <p>Created by author <?= out::h($campaign->author) ?> on
    <abbr class="create date" title="<?= out::h($campaign->date_created) ?>"><?= date('n-j-Y g:ia', strtotime($campaign->date_created)) ?></abbr></p>
    for users who crashed on
    <code><?= out::h($campaign->signature) ?></code> between 
    <abbr class="start date" title="<?= out::h($campaign->start_date) ?>"><?= date('n-j-Y g:ia', strtotime($campaign->start_date)) ?></abbr> and 
    <abbr class="end date"   title="<?= out::h($campaign->end_date)   ?>"><?= date('n-j-Y g:ia', strtotime($campaign->end_date)) ?></abbr>.</p>

    <p>Here are the contents of the email subject and then body. Note: Variables present below were 
       replaced with personalized values.</p>
  <hr />
  <h3><?= out::h($campaign->subject) ?></h3>
  <pre><?= out::h($campaign->body) ?></pre>
  <hr />
  <input type="hidden" name="campaign_id" value="<?= out::H($campaign->id) ?>" />

  <input name="token"  type="hidden" value="<?= $csrf_token ?>" />
  <?php if ($campaign->status == 'stopped') { ?>
    <input name="submit" type="submit" value="OK, Send Emails" />
  <?php } else { ?>
    <input name="submit" type="submit" value="STOP Sending Emails" />
  <?php  }?>
<?php } else { ?>
  Unable to load campaign.
<?php  }?>
