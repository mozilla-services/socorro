/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */



<div class="panel">
	<div class="title">
		<h2>Mozilla Products in Crash Reporter</h2>
    </div>

    <div class="body">
    <p>
        <ul>
        <?php foreach ($products as $product) { ?>
            <li><a href="<?php echo url::site('products/'.$product); ?>"><?php out::H($product); ?></a></li>
        <?php } ?>
        </ul>
    </p>
    </div>

</div>
