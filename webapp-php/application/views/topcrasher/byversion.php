<?php slot::start('head') ?>
    <title>Top Crashers for  <?php out::H($product) ?> <?php out::H($version) ?></title>
    <link title="CSV formatted Top Crashers for  <?php out::H($product) ?> <?php out::H($version) ?>"
          type="text/csv" rel="alternate" href="?format=csv" />
    <?php echo html::script(array(
       'js/jquery/plugins/ui/jquery.tablesorter.min.js',
       'js/jquery/plugins/jquery.girdle.min.js',
       'js/socorro/topcrash.js',
       'js/socorro/bugzilla.js',
       'js/socorro/correlation.js'
    ))?>
    <?php echo html::stylesheet(array(
        'css/flora/flora.tablesorter.css'
    ), 'screen')?>

<?php slot::end() ?>


<div class="page-heading">
	<h2>Top Crashers for <span class="current-product"><?php out::H($product) ?></span> <span class="current-version"><?php out::H($version) ?></span></h2>
    <ul class="options">
        <li><a href="<?php echo url::base(); ?>topcrasher/byversion/<?php echo $product ?>/<?php echo $version ?>" class="selected">By Signature</a></li>
        <li><a href="<?php echo url::base(); ?>topcrasher/byurl/<?php echo $product ?>/<?php echo $version ?>">By URL</a></li>
        <li><a href="<?php echo url::base(); ?>topcrasher/bydomain/<?php echo $product ?>/<?php echo $version ?>">By Domain</a></li>
        <li><a href="<?php echo url::base(); ?>topcrasher/bytopsite/<?php echo $product ?>/<?php echo $version ?>">By Topsite</a></li>
    </ul>
</div>


<div class="panel content-wrap">
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
