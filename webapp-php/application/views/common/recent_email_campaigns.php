<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<h3>Recent Campaigns</h3>
<?php if (count($campaigns) > 0) { ?>
<table class="recent-campaigns data-table">
    <thead>
        <tr>
            <th>ID</th>
            <th>Date</th>
            <th>Signature</th>
            <th>Author</th>
        </tr>
    </thead>
    <tbody>
    <?php foreach($campaigns as $campaign) { ?>
        <tr>
            <td><a href="<?= url::site("/admin/email_campaign/" . $campaign->id) ?>"><?= out::H($campaign->id) ?></a></td>
            <td><?= out::H($campaign->start_date) ?></td>
            <td><?= out::H($campaign->signature) ?></td>
            <td><?= $campaign->author ?></td>
        </tr>
    <?php } ?>
    </tbody>
</table>
<?php } else { ?>
    <p>No campaigns yet.</p>
<?php } ?>
