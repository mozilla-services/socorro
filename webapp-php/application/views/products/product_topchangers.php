
<?php slot::start('head') ?>
    <?php echo html::link(array($url_rss), 'alternate', array('application/rss+xml'), FALSE); ?>
    <title>Top Changing Top Crashers for <?php out::H($product) ?></title>
<?php slot::end() ?>


<div class="page-heading">
    <h2>
        Top Changers for <?php out::H($product) ?>
        <?php
            if (isset($version) && !empty($version)) {
                out::H($version);
            } elseif (isset($versions) && !empty($versions)) {
                out::H(implode(", ", $versions));
            }
        ?>
    </h2>

    <ul class="options">
        <li><a href="<?php out::H($url_base); ?>/topchangers?duration=3" <?php if ($duration == 3) echo ' class="selected"'; ?>>3 days</a></li>
        <li><a href="<?php out::H($url_base); ?>/topchangers?duration=7" <?php if ($duration == 7) echo ' class="selected"'; ?>>7 days</a></li>
        <li><a href="<?php out::H($url_base); ?>/topchangers?duration=14" <?php if ($duration == 14) echo ' class="selected"'; ?>>14 days</a></li>
        <li><a href="<?php out::H($url_base); ?>/topchangers?duration=28" <?php if ($duration == 28) echo ' class="selected"'; ?>>28 days</a></li>
    </ul>
</div>

<div class="panel">
    <div class="body notitle">

    <?php
    View::factory('common/product_topchangers', array(
        'duration' => $duration,
        'product' => $product,
        'top_changers' => $top_changers
    ))->render(TRUE);
    ?>

    <p><a href="<?php echo url::base() . $url_csv; ?>">Download CSV</a></p>
    <p><a href="<?php echo url::base() . $url_rss; ?>">Subscribe to RSS</a></p>
    </div>
</div>


