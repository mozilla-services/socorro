<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<?php if(property_exists($crasher, 'startup_crash') && $crasher->startup_crash) { ?>
        <img src="<?= url::site('/img/icons/rocket_fly.png')?>" width="16" height="16" alt="Startup Crash" title="Startup Crash" class="startup" />
<?php } ?>
<?php
$linked = false;
if (isset($crasher->{'link'}) && !empty($crasher->{'link'})) {
    $linked = true;
}
if (isset($crasher->{'content_count'}) && $crasher->{'content_count'} > 0) { 
    if ($linked) { ?>
        <a href="<?= $crasher->{'link'} ?>" class="content-btn" title="Content Crash">
    <?php } ?>
        <img src="<?= url::site('/img/3rdparty/fatcow/content16x16.png')?>" width="16" height="16" alt="Content Crash" title="Content Crash" class="content" />
    <?php if ($linked) { echo '</a>'; }
} ?>

<?php 
if ($crasher->{'hang_count'} > 0) { 
    if ($linked) { ?>
        <a href="<?= $crasher->{'link'} ?>" class="hang-pair-btn" title="Hanged Crash">
    <?php } ?>
        <img src="<?= url::site('/img/3rdparty/fatcow/stop16x16.png')?>" width="16" height="16" alt="Hanged Crash" title="Hanged Crash" class="hang" />
    <?php if ($linked) { echo '</a>'; }
} ?>

<?php 
if ($crasher->{'plugin_count'} > 0) {
    if ($linked) { ?>
        <a href="<?= $crasher->{'link'} ?>" class="plugin-btn" title="Plugin Crash">
    <?php } ?>
        <img src="<?= url::site('/img/3rdparty/fatcow/brick16x16.png')?>" width="16" height="16" alt="Plugin Crash" title="Plugin Crash" class="plugin" class="plugin" />
    <?php if ($linked) { echo '</a>'; }
} ?>

<?php 
if ($crasher->{'count'} > $crasher->{'plugin_count'}) {
    if ($linked) { ?>
        <a href="<?= $crasher->{'link'} ?>" class="hang-pair-btn" title="Browser Crash">
    <?php } ?>
        <img src="<?= url::site('/img/3rdparty/fatcow/application16x16.png')?>" width="16" height="16" alt="Browser Crash" title="Browser Crash" class="browser" />
    <?php if ($linked) { echo '</a>'; }
} ?>
