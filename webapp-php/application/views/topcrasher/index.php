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
          <td class="sig"><a href="<?php out::H($link_url)?>"
            title="<?php out::H($sig)?>"><?php out::H($sig)?></a></td>
          <td><?php out::H($crasher->total)?></td>
        </tr>
        <?php endforeach; ?>
        </tbody>
      </table>

      <?php $url = url::base() . "topcrasher/byversion/{$prodversion['product']}/{$prodversion['version']}" ?>
      <p><a href="<?php out::H($url)?>">View all current crashers</a></p>
      </div>
    <?php endforeach; ?>

    <h1>Other Versions</h1>
    <div class="other_vers">
      <?php
      foreach ($all_versions as $product => $versions):
        $ver_count = count($all_versions[$product]);
        $first = $all_versions[$product][$ver_count-1];
        $last = $all_versions[$product][0];
        ?>
        <div class="other_ver">
          <form method="get" action="<?php echo url::base().'topcrasher/byversion'?>">
            <h2><?php out::H($product)?></h2>
            <input type="hidden" name="product" value="<?php out::H($product)?>"/>
            <select name="version" onchange="this.form.submit()">
              <option value=""><?php out::H($first)?>&ndash;<?php out::H($last)?></option>
              <option value="">---</option>
              <?php foreach ($versions as $version): ?>
              <option value="<?php out::H($version)?>"><?php out::H($version)?></option>
              <?php endforeach; ?>
            </select>
            <noscript><button type="submit">Go</button></noscript>
          </form>
        </div>
      <?php endforeach; ?>
      <div class="clear"></div>
    </div>
</div>

