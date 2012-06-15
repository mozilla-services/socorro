
<?php slot::start('head') ?>
    <?php echo html::link(array($url_rss), 'alternate', array('application/rss+xml'), FALSE); ?>
    <title>Nightly Builds for <?php out::H($product) ?> <?php out::H($version); ?></title>
<?php slot::end() ?>

<?php
View::factory('common/product_builds', array(
    'builds' => $builds,
    'dates' => $dates,
    'product' => $product,
    'version' => $version,
    'versions' => $versions
))->render(TRUE);
?>


