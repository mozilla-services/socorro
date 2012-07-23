<?php foreach ($channels as $c) { ?>
    <option value="<?php out::H($c); ?>" <?php if (isset($channel) && ($c == $channel)) { ?> selected="selected" <?php } ?>>
        <?php out::H($c); ?>
    </option>
<?php } ?>
