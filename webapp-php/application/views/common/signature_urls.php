/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<div id="sigurls" class="ui-tabs-hide">
    <table class="data-table">
        <thead>
            <tr>
                <th>Total Count</th>
                <th>URL</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($urls as $url) { ?>
            <tr>
                <td><?php out::H($url->crash_count); ?></td>
                <td>
                    <?php $display_url = substr($url->url, 0, 80); ?>
                    <a href="<?php out::H($url->url); ?>" title="<?php out::H($url->url); ?>"><?php out::H($display_url); ?></a>
                </td>
            </tr>
        <?php } ?>
        </tbody>
    </table>
</div>