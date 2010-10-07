<?php if (isset($campaign)) { ?>
  <h1>PostCrash Email Campaign</h2>
  <h2><?= out::h($campaign->product) ?> <?= out::h($campaign->versions) ?></h2>
  <p><?= out::h($campaign->author) ?> emailed <?= out::h($campaign->email_count)?>  users who crashed on
    <code><?= out::h($campaign->signature) ?></code> between 
    <abbr class="start date" title="<?= $campaign->start_date ?>"><?= date('n-j-Y g:ia', strtotime($campaign->start_date)) ?></abbr> and 
    <abbr class="end date"   title="<?= $campaign->end_date   ?>"><?= date('n-j-Y g:ia', strtotime($campaign->end_date)) ?></abbr>.</p>

    <p>Email sent <abbr class="create date" title="<?= $campaign->date_created ?>"><?= date('n-j-Y g:ia', strtotime($campaign->date_created)) ?></abbr></p>
    <p>Here are the contents of the email subject and then body. Note: Variables present below were 
       replaced with personalized values.</p>
  <hr />
  <h3><?= out::h($campaign->subject) ?></h3>
  <pre><?= out::h($campaign->body) ?></pre>
<?php } else { ?>
  Unable to load campaign.
<?php  }?>