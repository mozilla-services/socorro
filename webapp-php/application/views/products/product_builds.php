
<?php slot::start('head') ?>
    <?php echo html::link(array($url_rss), 'alternate', array('application/rss+xml'), FALSE); ?>
    <title>Nightly Builds for <?php out::H($product) ?></title>
<?php slot::end() ?>


<?php
View::factory('common/product_builds', array(
    'builds' => $builds,
    'dates' => $dates,
    'product' => $product,
    'versions' => $versions
))->render(TRUE);
?>


