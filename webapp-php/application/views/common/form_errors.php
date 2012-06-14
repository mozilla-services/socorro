/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

     <?php if (isset($has_errors) && $has_errors) { ?>
        <h3>Errors</h3>
        <p>Please <strong>fix the following errors</strong> and try again.</p>
        <ul class="errors">
          <?php foreach ($errors as $key => $value) { ?>
            <li><?= $value ?></li>
          <?php } ?>
        </ul>
      <?php } ?>
