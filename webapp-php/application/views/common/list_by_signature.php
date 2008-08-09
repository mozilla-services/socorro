<table id="signatureList" class="tablesorter">
    <thead>
        <tr>
            <th>Rank</th>
            <th>Signature</th>
            <?php if (count($platforms) > 1): ?><th>#</th><?php endif ?>
            <?php foreach ($platforms as $platform): ?>
                <th><?php out::H(substr($platform->name, 0, 3)) ?></th>
            <?php endforeach ?>
        </tr>
    </thead>
    <tbody>
        <?php $row = 1 ?>
        <?php foreach ($reports as $report): ?>
            <tr class="<?php echo ( ($row-1) % 2) == 0 ? 'even' : 'odd' ?>">
                <td><?php out::H($row) ?></td>
                <td>
                    <?php
                        $url_params = $params;
                        $url_params['signature'] = $report->signature;
                        $url = url::base().'report/list?'.html::query_string($url_params);
                    ?><a href="<?php out::H($url) ?>" title="View reports with this signature."><?php out::H($report->signature) ?></a>
                </td>
                <?php if (count($platforms) > 1): ?><th><?php out::H($report->count) ?></th><?php endif ?>
                <?php foreach ($platforms as $platform): ?>
                    <td><?php out::H($report->{'is_'.$platform->id}) ?></td>
                <?php endforeach ?>
            </tr>
            <?php $row += 1 ?>
        <?php endforeach ?>
    </tbody>
</table>
