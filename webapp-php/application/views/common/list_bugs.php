/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<div class="bug_ids_expanded_list">
<?php if (! isset($suppressHeader)) { ?>
    <h3>Bugs for <code><?= out::H($signature) ?></code></h3>
<?php } ?>
  <ul class="bug_ids_expanded full_bug_ids <?= $mode ?>">
    <?php
    foreach ($bugs as $bug) {  ?>
        <li><?php View::factory('common/bug_number')
                      ->set('bug', $bug)
                      ->set('mode', $mode)
                      ->render(TRUE);?></li>
    <?php } ?>
  </ul>
</div>
