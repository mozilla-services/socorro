<?php slot::start('head') ?>
  <title>Top Crashers</title>
<?php slot::end() ?>
<div id="topcrashers">
    <h1>Top Crashers</h1>
    <?php foreach ($crasher_data as $prodversion): ?>
      <div class="crasher_list">
      <h2><?=$prodversion['product']?> <?=$prodversion['version']?></h2>
      <table summary="List of top crashes for <?php out::H($prodversion['product'].' '.$prodversion['version'])?>">
        <thead>
        <tr>
          <th>Signature</th>
          <th title="Crash Count">&nbsp;</th>
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
          <td class="sig"><a href="<?php out::H($link_url)?>"><?php out::H($sig)?></a></td>
          <td><?php out::H($crasher->total)?></td>
        </tr>
        <?php endforeach; ?>
        </tbody>
      </table>

      <?php $url = url::base() . "topcrasher/byversion/{$prodversion['product']}/{$prodversion['version']}" ?>
      <p><a href="<?php out::H($url)?>">View all current crashers</a></p>
      </div>
    <?php endforeach; ?>
</div>

