<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<?php slot::start('head') ?>
    <title>Top Crashers for  <?php out::H($product) ?> <?php out::H($version) ?></title>
    <link title="CSV formatted Top Crashers for  <?php out::H($product) ?> <?php out::H($version) ?>"
          type="text/csv" rel="alternate" href="?format=csv" />
    <?php echo html::script(array(
       'js/jquery/plugins/ui/jquery.tablesorter.min.js',
       'js/socorro/topcrash.js',
       'js/socorro/bugzilla.js',
       'js/socorro/correlation.js'
    ))?>
    <?php echo html::stylesheet(array(
        'css/flora/flora.tablesorter.css'
    ), 'screen')?>

<?php slot::end() ?>


<div class="page-heading">
    <h2>Top Crashers for <span id="current-product"><?php out::H($product) ?></span> <span id="current-version"><?php out::H($version) ?></span></h2>
    <ul class="options">
        <li><a href="<?php echo url::base(); ?>topcrasher/byversion/<?php echo $product ?>/<?php echo $version ?>" class="selected">By Crash Date</a></li>
        <li><a href="<?php echo url::base(); ?>topcrasher/by_build_date/<?php echo $product ?>/<?php echo $version ?>">By Build Date</a></li>
    </ul>
</div>


<div class="panel">
    <div class="body notitle">
<?php
if ($resp) {
    View::factory('common/list_topcrashers', array(
              'last_updated' => $last_updated,
              'top_crashers' => $top_crashers
              ))->render(TRUE);
} else {
    View::factory('common/data_access_error')->render(TRUE);
}
?>
    </div>
</div>
