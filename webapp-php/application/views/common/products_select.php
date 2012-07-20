<?php foreach ($products as $p) { ?>
    <option value="<?php out::H($p); ?>" <?php if (isset($product) && ($p == $product)) { ?> selected="selected" <?php } ?>>
        <?php out::H($p); ?>
    </option>
<?php } ?>
