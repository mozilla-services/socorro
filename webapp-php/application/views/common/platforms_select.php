<?php foreach ($platforms as $p) { ?>
    <option value="<?php out::H($p); ?>" <?php if (isset($platform) && ($p == $platform)) { ?> selected="selected" <?php } ?>>
        <?php out::H($p); ?>
    </option>
<?php } ?>
