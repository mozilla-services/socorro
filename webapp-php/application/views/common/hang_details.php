<?php /* Hang widget used from individual reports or aggregate views.
Requires: array named crash with keys
* is_hang - Is this crash a hang crash
* is_plugin - Is this hang crash ta plugin (oopp)?
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
    <?php if ($linked) { ?><a href="<?= $crash['link'] ?>" class="hang-pair-btn"><?php } ?><img src="<?= url::site('/img/3rdparty/fatcow/stop16x16.png')?>" width="16" height="16" alt="Hanged Crash" class="hang" /><?php if ($linked) { echo '</a>'; } ?>
    <?php if ($crash['is_plugin'] == true) {?>
																													      <?php if ($linked) { ?><a href="<?= $crash['link'] ?>" class="hang-pair-btn"><?php } ?><img src="<?= url::site('/img/3rdparty/fatcow/brick16x16.png')?>" width="16" height="16" alt="Plugin Crash" class="plugin" /><?php if ($linked) { echo '</a>'; } ?>
     <?php } else { ?>
	      <?php if ($linked) { ?><a href="<?= $crash['link'] ?>" class="hang-pair-btn"><?php } ?><img src="<?= url::site('/img/3rdparty/fatcow/application16x16.png')?>" width="16" height="16" alt="Browser Crash" class="browser" /><?php if ($linked) { echo '</a>'; } ?>
    <?php }
} else { ?>
    <div class="no-hang"></div>
<?php }
?>
