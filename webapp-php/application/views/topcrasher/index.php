<?php slot::start('head') ?>
  <title>Top Crashers</title>
<?php slot::end() ?>
<p><strong>Note</strong> this page is end of lifed. Please use <a href="<?php echo url::base() ?>">the homepage</a> for a list of top crashers.</p>
<h1>Top Crashers by Version</h1>
 <ul>
    <?php foreach ($all_versions as $row): ?>
      <li>
          <?php $url = url::base() . "topcrasher/byversion/{$row->product}/{$row->version}" ?>
          <a href="<?php out::H($url) ?>"><?php out::H( $row->product . ' ' . $row->version ) ?></a>
      </li>
    <?php endforeach ?>
 </ul>

