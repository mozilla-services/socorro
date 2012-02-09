<td>
<?php if (array_key_exists($crasher->signature, $sig2bugs)) {
    $bugs = $sig2bugs[$crasher->signature];
    $bugCount = count($bugs);
    for ($i = 0; $i < 3 and $i < $bugCount; $i++) {
        $bug = $bugs[$i];
        View::factory('common/bug_number')->set('bug', $bug)->render(TRUE);
        echo ", ";
    } ?>
    <div class="bug_ids_extra">
        <?php for ($i = 3; $i < $bugCount; $i++) {
            $bug = $bugs[$i];
            View::factory('common/bug_number')->set('bug', $bug)->render(TRUE);
        } ?>
    </div>
    <?php if ($bugCount > 0) { ?>
        <a href='#' title="Click to See all likely bug numbers" class="bug_ids_more">More</a>
        <?php View::factory('common/list_bugs', array(
            'signature' => $crasher->signature,
            'bugs' => $bugs,
            'mode' => 'popup'
        ))->render(TRUE);
    }
} ?>
</td>