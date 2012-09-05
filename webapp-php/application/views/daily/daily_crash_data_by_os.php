<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>

<div class="panel daily_">
    <div class="title">
        <h2>Crashes per ADU</h2>
        <div class="choices">
            <ul>
                <li><a href="<?php echo $url_csv; ?>">csv</a></li>
            </ul>
        </div>
    </div>

    <div class="body">

    <?php if (isset($statistics['os']) && !empty($statistics['os'])) { ?>

        <table class="data-table crash_data zebra">
            <tr>
                <th class="date" rowspan="2">Date</th>
                <?php foreach ($operating_systems as $key => $os) { ?>
                    <?php if (!empty($os)) { ?>
                        <th class="os" colspan="4"><?php out::H($os); ?></th>
                    <?php } ?>
                <?php } ?>
                </tr>
                <tr>
                <?php foreach ($operating_systems as $os) { ?>
                    <?php if (!empty($os)) { ?>
                        <th class="stat">Crashes</th>
                        <th class="stat">ADU</th>
                        <th class="stat" title="The throttle rate is the effective throttle rate - the combined throttle rate for client-side throttling and server-side throttling.">Throttle</th>
                        <th class="stat">Ratio</th>
                    <?php } ?>
                <?php } ?>
            </tr>

            <?php foreach ($dates as $date) { ?>
                <tr>
                    <td><?php out::H($date); ?></td>

                    <?php
                        foreach ($operating_systems as $os) {
                    ?>

                                <td><?php
                                    if (isset($statistics['os'][$os][$date]['crashes'])) {
                                        out::H(number_format(round($statistics['os'][$os][$date]['crashes'])));
                                    } else {
                                        echo '-';
                                    }
                                ?></td>
                                <td><?php
                                    if (isset($statistics['os'][$os][$date]['users'])) {
                                        out::H(number_format(round($statistics['os'][$os][$date]['users'])));
                                    } else {
                                        echo '-';
                                    }
                                ?></td>
                                <td title="The throttle rate is the effective throttle rate - the combined throttle rate for client-side throttling and server-side throttling."><?php
                                    if (isset($statistics['os'][$os][$date]['throttle'])) {
                                        out::H($statistics['os'][$os][$date]['throttle']*100);
                                        echo '%';
                                    } else {
                                        echo '-';
                                    }
                                ?></td>
                                <td><?php
                                    if (isset($statistics['os'][$os][$date]['ratio'])) {
                                        $ratio = round($statistics['os'][$os][$date]['ratio'] * 100, 2);
                                        out::H($ratio);
                                        echo "%";
                                    } else {
                                        echo '-';
                                    }
                                ?></td>
                    <?php
                            }
                    ?>
                </tr>
            <?php } ?>

            <tr>
                <td class="date"><strong>Total</strong></td>
            <?php
                foreach($operating_systems as $os) {
            ?>
                <td class="stat"><strong><?php
                    if (isset($statistics['os'][$os]['crashes'])) {
                        out::H(number_format(round($statistics['os'][$os]['crashes'])));
                    }
                ?></strong></td>
                <td class="stat"><strong><?php
                    if (isset($statistics['os'][$os]['users'])) {
                        out::H(number_format(round($statistics['os'][$os]['users'])));
                    }
                ?></strong></td>
                <td class="stat" title="The throttle rate is the effective throttle rate - the combined throttle rate for client-side throttling and server-side throttling."><strong><?php
                    if (isset($statistics['os'][$os]['throttle'])) {
                        out::H($statistics['os'][$os]['throttle'] * 100);
                        echo '%';
                    }
                ?></strong></td>
                <td class="stat"><strong><?php
                    if (isset($statistics['os'][$os]['ratio'])) {
                        $ratio = round($statistics['os'][$os]['ratio'] * 100, 2);
                        out::H($ratio);
                        echo "%";
                    }
                ?></strong></td>

            <?php
                }
            ?>
            </tr>

        </table>

    <?php } else { ?>

        <p>No data is available for this query.</p>

    <?php } ?>

    </div>

</div>
