/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */


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


