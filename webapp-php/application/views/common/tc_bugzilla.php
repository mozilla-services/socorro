/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<td class="bug_ids_more">
<?php if (array_key_exists($crasher->signature, $sig2bugs)) {
    $bugs = $sig2bugs[$crasher->signature];
    $bugCount = count($bugs);
    for ($i = 0; $i < 3 and $i < $bugCount; $i++) {
        $bug = $bugs[$i];
        View::factory('common/bug_number')->set('bug', $bug)->render(TRUE);
        echo ", ";
    } echo " ..."; ?>
    <div class="bug_ids_extra">
        <?php for ($i = 3; $i < $bugCount; $i++) {
            $bug = $bugs[$i];
            View::factory('common/bug_number')->set('bug', $bug)->render(TRUE);
        } ?>
    </div>
    <?php if ($bugCount > 0) { ?>
        <?php View::factory('common/list_bugs', array(
            'signature' => $crasher->signature,
            'bugs' => $bugs,
            'mode' => 'popup'
        ))->render(TRUE);
    }
} ?>
</td>