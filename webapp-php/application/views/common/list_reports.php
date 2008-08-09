<table class="tablesorter" id="reportsList">
    <thead>
        <tr>
            <th>Date</th>
            <th>Product</th>
            <th>Version</th>
            <th>Build</th>
            <th>OS</th>
            <th>CPU</th>
            <th>Reason</th>
            <th>Address</th>
            <th>Uptime</th>
            <th>Comments</th>
        </tr>
    </thead>
    <tbody>
        <?php foreach ($reports as $report): ?>
            <tr>
                <td class="report-date">
                    <?php
                        $date_processed = strtotime($report->date_processed);
                        $url = url::base().'report/index/'.out::H($report->uuid, FALSE);
                    ?><a href="<?php out::H($url) ?>" title="View reports with this signature.">
                        <?php echo date('Y-m-d', $date_processed) ?>&nbsp;<?php echo date('H:i', $date_processed) ?>
                    </a>
                </td> <td><?php out::H($report->product) ?></td>
                <td><?php out::H($report->version) ?></td>
                <td><?php out::H($report->build) ?></td>
                <td><?php out::H($report->os_name) ?> <?php out::H($report->os_version) ?></td>
                <td><?php out::H($report->cpu_name) ?></td>
                <td><?php out::H($report->reason) ?></td>
                <td><?php out::H($report->address) ?></td>
                <td><?php out::H($report->uptime) ?></td>
                <td><?php out::H($report->comments) ?></td>
            </tr>
        <?php endforeach ?>
    </tbody>
</table>
