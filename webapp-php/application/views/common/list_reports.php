<table class="tablesorter" id="reportsList">
    <thead>
        <tr>
            <th>Date</th>
            <th>Dup</th>
            <th>Product</th>
            <th>Version</th>
            <th>Build</th>
            <th>OS</th>
            <th>CPU</th>
            <th>Reason</th>
            <th>Address</th>
            <th>Hang</th>
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
                        $date = strtotime($report->date_processed);
                        // TODO: Find out why this is not $date = strtotime($report->date);
                        $url = url::base().'report/index/'.out::H($report->uuid, FALSE);
                    ?><a href="<?php out::H($url) ?>">
                        <?php echo date('M d, Y H:i', $date) ?>
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
                <td><?php out::H(date("Y-m-d H:i:s", strtotime($report->install_time))); ?></td>
                <td class="comments"><?php out::H($report->user_comments) ?></td>
            </tr>
        <?php 
	       $i++;
           endforeach ?>
    </tbody>
</table>
