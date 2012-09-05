<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<?php if (isset($products) && !empty($products)) { ?>
    <form name="update_featured" id="update_featured" action="" method="post">
    <?php foreach ($products_list as $product) { ?>
        <h4><?php echo html::specialchars($product); ?></h4>
        <table data-product="<?php echo html::specialchars($product); ?>">
            <thead>
                <tr>
                <th>Product</th>
                <th>Version</th>
                <th>Release</th>
                <th>Start Date</th>
                <th>End Date</th>
                <th>Featured</th>
                <th>Throttle</th>
                </tr>
            </thead>
            <tbody>
            <?php foreach ($versions as $version) { ?>
                <?php if ($version->product == $product) {
                        $current_product = html::specialchars($version->product);
                        $current_version = html::specialchars($version->version);
                    ?>
                    <tr>
                        <td class="text"><?php echo html::specialchars($current_product); ?></td>
                        <td class="text"><?php echo html::specialchars($current_version); ?></td>
                        <td class="text"><?php echo html::specialchars(html::specialchars($version->release)); ?></td>
                        <td class="date"><?php
                            if (isset($version->start_date)) {
                                echo html::specialchars(str_replace('00:00:00', '', $version->start_date));
                            }
                        ?></td>
                        <td class="date"><?php
                            if (isset($version->end_date)) {
                                echo html::specialchars(str_replace('00:00:00', '', $version->end_date));
                            }
                        ?></td>
                        <td class="featured">
                            <input type="checkbox"
                                name="<?php echo html::specialchars($current_product); ?>"
                                value="<?php echo html::specialchars($current_version); ?>"
                                <?php if (isset($version->featured) && $version->featured == 't') { echo "checked='checked'"; } ?> />
                        </td>
                        <td class="throttle"><?php
                            if (isset($version->throttle) && $version->throttle > 0) {
                                out::H($version->throttle);
                            } else {
                                echo '-.--';
                            }
                        ?>%</td>
                    </tr>
                <?php } ?>
            <?php } ?>
                <tr>
                    <td colspan="7">
                        <input class="update_featured_btn" type="submit" name="<?php echo $current_product; ?>" value="Update Featured Versions" />
                    </td>
                </tr>
            </tbody>
        </table>
    <?php } ?>
    <div class="user-msg"></div>
    </form>
<?php } ?>
