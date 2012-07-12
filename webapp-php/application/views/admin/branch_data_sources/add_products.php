<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<form name="add_product" id="add_product" action="" method="post">
    <legend>Add A New Product Release</legend>
    <fieldset>
        <div class="field">
            <label for="product">Product Name:</label>
            <input type="text" name="product" id="product" required />
        </div>
        <div class="field">
            <label for="version">Version:</label>
            <input type="text" name="version" id="version" required />
        </div>
        <div class="field">
            <label for="release_channel">Release Channel:</label>
            <input type="text" name="release_channel" id="release_channel" required />
        </div>
        <div class="field">
            <label for="build_id">Build ID:</label>
            <input type="text" name="build_id" id="build_id" required />
        </div>
        <div class="field">
            <label for="platform">Platform</label>
            <input type="text" name="platform" id="platform" required />
        </div>
        <div class="field">
            <label for="repository">Repository:</label>
            <input type="text" name="repository" id="repository" required />
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
