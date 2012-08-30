<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<form name="add_release" id="add_release" action="" method="post">
    <legend>Add A New Product Release</legend>
    <fieldset>
        <div class="field">
            <label for="product">Product Name:</label>
            <select id="product" name="product">
                <?php View::factory('common/products_select', array('products' => $products_list))->render(TRUE); ?>
            </select>
        </div>
        <div class="field">
            <label for="version">Version:</label>
            <input type="text" name="version" id="version" placeholder="ex. 16.0a1" data-required="true" />
        </div>
        <div class="field">
            <label for="release_channel">Release Channel:</label>
            <select id="release_channel" name="release_channel">
                <?php View::factory('common/release_channels_select', array('channels' => $release_channels))->render(TRUE); ?>
            </select>
        </div>
        <div class="field">
            <label for="build_id">Build ID:</label>
            <input type="text" name="build_id" id="build_id" placeholder="format: YYYYMMDDhhmmss" data-required="true" data-requiredlength="14" />
        </div>
        <div class="field">
            <label for="platform">Platform</label>
            <select id="platform" name="platform">
                <?php View::factory('common/platforms_select', array('platforms' => $platforms))->render(TRUE); ?>
            </select>
        </div>
        <div class="field">
            <label for="repository">Repository:</label>
            <input type="text" name="repository" id="repository" data-required="true" />
        </div>
        <h4 class="collapsed"><a href="#optional" id="optional-fields-toggle" title="Click/Tap to show and hide optional fields">Optional Fields</a></h4>
        <section class="optional optional-collapsed">
            <div class="field">
                <label for="beta_number">Beta Number (Optional)</label>
                <input type="text" name="beta_number" id="beta_number" />
            </div>
        </section>

        <input type="submit" name="add" value="Add Product" />
    </fieldset>
</form>
