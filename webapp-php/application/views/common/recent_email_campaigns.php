  <div class="sidebar body">
    <h3>Recent Campaigns</h3>
    <?php if (count($campaigns) > 0) { ?>
      <table class="recent-campaigns">
        <?php foreach($campaigns as $campaign) { ?>
          <tr class="signature"><td colspan="7"><?= $campaign->signature ?></td></tr>
          <tr class="details"><th>ID</th><td><a href="<?= url::site("/admin/email_campaign/" . $campaign->id) ?>"
                                                 ><?= $campaign->id ?></a></td><th>Date</th><td><?= $campaign->start_date ?></td>
                              <th>Author</th><td><?= $campaign->author ?></td>
          </tr>
        <?php } ?>
      </table>
      <p><a href="email_campaigns">See All Campaigns</a></p>
    <?php } else { ?>
      <p>No campaigns yet.</p>
    <?php } ?>    
  </div><!-- .sidebar -->