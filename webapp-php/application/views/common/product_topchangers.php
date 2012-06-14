/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */


<?php if (isset($top_changers) && !empty($top_changers)) { ?>
    <div>
    <?php foreach ($top_changers as $key => $changers) { ?>
        <div class="product_topchanger<?php if ($key == 'up' && !$topchangers_full_page) echo ' border_right'; ?>">
            <table id="top_changers_<?= $key; ?>" class="top_changers">
                <tr>
                    <th>Change</th>
                    <th>Rank</th>
                    <th>Signature</th>
                </tr>
                <?php function changer_row($top_changer) { ?>
                    <tr>
                        <td><div class="trend <?= $top_changer['trendClass'] ?>"><?= $top_changer['changeInRank']; ?></div></td>
                        <td><?= ($top_changer['currentRank']); ?></td>
                        <td><a class="signature" href="<?= ($top_changer['url']); ?>"
                           title="View reports with this crasher."><?php out::H($top_changer['signature']); ?></a>
                        </td>
                    </tr>
                <?php } ?>
                <?php
                    foreach ($changers as $changer) {
                        if(!is_null($changer['signature']) and !empty($changer['signature'])) {
                            changer_row($changer);
                        }
                    } ?>
            </table>
        </div>
    <?php } ?>
    <br class="clear">
    </div>
<?php } else { ?>
    <p>There were no top changers that matched the criteria you specified.</p>
<?php } ?>
