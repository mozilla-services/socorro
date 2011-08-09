<?php /* Hang widget used from individual reports or aggregate views.
Requires: array named crash with keys
* is_hang - Is this crash a hang report
* is_plugin - Is this crash a plugin (oopp) or hang report, plugin part
Optional:
* uuid  - current reprots's uuid
* hangid - current report's hangid
If uuid and hangid are preesnt, then AJAX widget will be enabled to show the hang's pair
*/
$linked = false;
if (array_key_exists('link', $crash)) {
    $linked = true;
}
if ($crash['is_hang'] == true) { ?>
    <?php if ($linked) { ?><a href="<?= $crash['link'] ?>" class="hang-pair-btn" title="Hanged Crash"><?php } ?><img src="<?= url::site('/img/3rdparty/fatcow/stop16x16.png')?>" width="16" height="16" alt="Hanged Crash" title="Hanged Crash" class="hang" /><?php if ($linked) { echo '</a>'; } ?>
    <?php if ($crash['is_plugin'] == true) {?>
	      <?php if ($linked) { ?><a href="<?= $crash['link'] ?>" class="hang-pair-btn" title="Plugin Crash"><?php } ?><img src="<?= url::site('/img/3rdparty/fatcow/brick16x16.png')?>" width="16" height="16" alt="Plugin Crash" title="Plugin Crash" class="plugin" /><?php if ($linked) { echo '</a>'; } ?>
     <?php } else { ?>
	      <?php if ($linked) { ?><a href="<?= $crash['link'] ?>" class="hang-pair-btn" title="Browser Crash"><?php } ?><img src="<?= url::site('/img/3rdparty/fatcow/application16x16.png')?>" width="16" height="16" alt="Browser Crash" title="Browser Crash" class="browser" /><?php if ($linked) { echo '</a>'; } ?>
    <?php }
} else { ?>
    <?php if ($crash['is_plugin'] == true) {?>
              <?php if ($linked) { ?><a href="<?= $crash['link'] ?>" class="plugin-btn" title="Plugin Crash"><?php } ?><img src="<?= url::site('/img/3rdparty/fatcow/brick16x16.png')?>" width="16" height="16" alt="Plugin Crash" title="Plugin Crash" class="plugin" class="plugin" /><?php if ($linked) { echo '</a>'; } ?>
     <?php } ?>
<?php }
?>
