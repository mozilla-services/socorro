<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<table class="tablesorter data-table" id="reportsList">
    <thead>
        <tr>
            <th>Date</th>
            <th>Dup</th>
            <th>Product</th>
            <th>Version</th>
            <th>Build</th>
            <th>OS</th>
            <th>Build Arch</th>
            <th>Reason</th>
            <th>Address</th>
            <th>Crash Type</th>
            <th>Uptime</th>
            <th>Install Time</th>
            <th>Comments</th>
        </tr>
    </thead>
    <tbody>
        <?php
           $i = 0;
           foreach ($reports as $report): ?>
            <tr>
                <td class="report-date_processed">
                    <?php
                        $date = new DateTime($report->date_processed);
                        // TODO: Find out why this is not $date = strtotime($report->date);
                        $url = url::base().'report/index/'.out::H($report->uuid, FALSE);
                    ?><a href="<?php out::H($url) ?>">
                        <?php out::H($date->format('M d, Y H:i')) ?>
                    </a>
        <div class="hang-pair"></div>
                </td>
                <td><?php if (isset($report->duplicate_of) && !empty($report->duplicate_of)) {
                    echo '<a href="'.url::site("report/".html::specialchars($report->duplicate_of)).'"
                          title="This has been flagged as a possible duplicate crash report of '.html::specialchars($report->duplicate_of).'."
                          >dup</a>';
                } ?></td>
                <td><?php out::H($report->product) ?></td>
                <td><?php out::H($report->version) ?></td>
                <td><?php out::H($report->build) ?></td>
                <td><?php out::H($report->os_name) ?> <?php out::H($report->os_version) ?></td>
                <td><?php out::H($report->cpu_name) ?></td>
                <td><?php out::H($report->reason) ?></td>
                <td><?php out::H($report->address) ?></td>
                <td><div class="signature-icons">
        <?php View::factory('common/hang_details', array(
            'crash' => $report->{'hang_details'}
        ))->render(TRUE) ?>
        <input type="hidden" name="url<?= $i ?>" value="<?= url::site('/report/hang_pairs/' . $report->uuid) ?>" class="ajax_endpoint" />
        </div></td>
                <td><?php out::H($report->uptime) ?></td>
                <td><?php 
                     $install_time = new DateTime($report->install_time);
                    out::H($install_time->format("Y-m-d H:i:s")); ?></td>
                <td class="comments"><?php out::H($report->user_comments) ?></td>
            </tr>
        <?php
	       $i++;
           endforeach ?>
    </tbody>
</table>
