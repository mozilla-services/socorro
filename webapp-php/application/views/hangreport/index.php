<?php slot::start('head') ?>
  <title>Top Crashers</title>
  <?php echo html::stylesheet(array(
    'css/flora/flora.tablesorter.css'
  ), 'screen')?>
<?php slot::end() ?>
<div class="page-heading">
  <h2>Top Crashers</h2>
</div>

<?php foreach ($crasher_data as $prodversion): ?>
  <div class="panel">
    <div class="title">
      <h2><?=$prodversion['product']?> <?=$prodversion['version']?></h2>
    </div>
    <div class="body">
      <table
        class="tablesorter"
        summary="List of top crashes for <?php out::H($prodversion['product'].' '.$prodversion['version'])?>">
        <thead>
        <tr>
          <th class="header">Signature</th>
          <th class="header">Crash Count</th>
        </tr>
        </thead>
        <tbody>
        <?php foreach ($prodversion['crashers'] as $crasher): ?>
        <tr>
          <?php
            $sigParams = array(
              'range_value' => '2',
              'range_unit'  => 'weeks',
              'signature'   => $crasher->signature
            );
            if (property_exists($crasher, 'version')) {
              $sigParams['version'] = $crasher->product . ':' . $crasher->version;
            } else {
              $sigParams['branch'] = $crasher->branch;
            }
            $link_url =  url::base() . 'report/list?' . html::query_string($sigParams);

            if (empty($crasher->signature)) {
              $sig = '(no signature)';
            } else {
              $sig = $crasher->signature;
            }
          ?>
          <td class="sig"><a href="<?php out::H($link_url)?>"
            title="<?php out::H($sig)?>"><?php out::H($sig)?></a></td>
          <td class="count"><?php out::H($crasher->total)?></td>
        </tr>
        <?php endforeach; ?>
        </tbody>
      </table>

      <?php $url = url::base() . "topcrasher/byversion/{$prodversion['product']}/{$prodversion['version']}" ?>
      <p><a href="<?php out::H($url)?>">View all current crashers</a></p>
    </div>
  </div>
<?php endforeach; ?>
