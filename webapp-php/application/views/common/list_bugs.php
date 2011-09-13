<div class="bug_ids_expanded_list">
<?php if (! isset($suppressHeader)) { ?>
    <h3>Bugs for <code><?= out::H($signature) ?></code></h3>
<?php } ?>
<dl class="bug_ids_expanded <?= $mode ?>">
  <ul class="full_bug_ids <?= $mode ?>">
    <?php
    foreach ($bugs as $bug) {  ?>
        <li><?php View::factory('common/bug_number')
                      ->set('bug', $bug)
                      ->set('mode', $mode)
                      ->render(TRUE);?></li>
    <?php } ?>
  </ul>
</div>
