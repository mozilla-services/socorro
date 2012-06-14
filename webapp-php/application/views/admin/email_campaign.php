/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<?php if (isset($campaign)) { ?>
  <div class="page-heading">
    <h2>PostCrash Email Campaign</h3>
    <ul class="options">
        <li><a href="<?php echo url::base(); ?>admin/branch_data_sources">Branch Data Sources</a></li>
        <li><a href="<?php echo url::base(); ?>admin/email" class="selected">Email Users</a></li>
    </ul>
  </div>
  <div class="panel">
    <div class="title">
      <h2>Campaign <?= out::H($campaign->id) ?></h2>
    </div>
    <div class="body">
      <p>Product: <?= out::h($campaign->product) ?></p>
      <p>Versions: <?= out::h(str_replace(",", ", ", trim($campaign->versions, "()"))) ?></p>
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
      <pre class="email"><?= out::h($campaign->body) ?></pre>
      <hr />
      <input type="hidden" name="campaign_id" value="<?= out::H($campaign->id) ?>" />

      <input name="token"  type="hidden" value="<?= $csrf_token ?>" />
      <?php if ($campaign->status == 'stopped') { ?>
        <input name="submit" type="submit" value="OK, Send Emails" />
      <?php } else { ?>
        <input name="submit" type="submit" value="STOP Sending Emails" />
      <?php  }?>
    </div>
  </div>
<?php } else { ?>
  <h1>Unable to load campaign.</h1>
<?php  }?>
