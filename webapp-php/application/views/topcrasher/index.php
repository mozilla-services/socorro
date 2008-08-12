<?php slot::start('head') ?>
  <title>Top Crashers</title>
<?php slot::end() ?>

<h1>Top Crashers by Version</h1>
 <ul>
    <?php foreach ($all_versions as $row): ?>
      <li>
          <?php $url = url::base() . "topcrasher/byversion/{$row->product}/{$row->version}" ?>
          <a href="<?php out::H($url) ?>"><?php out::H( $row->product . ' ' . $row->version ) ?></a>
      </li>
    <?php endforeach ?>
 </ul>

