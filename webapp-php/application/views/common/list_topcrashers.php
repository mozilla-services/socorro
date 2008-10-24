<?php if (!$top_crashers): ?>
    <p>No results were found.</p>
<?php else: ?>
    <div>
        <?php if ($last_updated): ?>
       Below are the top <?php echo count($top_crashers) ?> crashers as of <?php out::H($last_updated) ?>.
        <?php else: ?>
       Below are the top <?php echo count($top_crashers) ?> crashers.
        <?php endif ?>
        <table class="tablesorter">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Signature</th>
                    <th>Build ID</th>
                    <th>#</th>
                    <th>Win</th>
                    <th>Lin</th>
                    <th>Mac</th>
                </tr>
            </thead>
            <tbody>
                <?php $row = 1 ?>
                <?php foreach ($top_crashers as $crasher): ?>
                    <?php
                        $link_url =  url::base() . 'report/list?' . html::query_string(array(
                            'range_value' => '2',
                            'range_unit'  => 'weeks',
                            'version'     => $crasher->product . ':' . $crasher->version,
                            'signature'   => $crasher->signature
                        ));
                    ?>
                    <tr class="<?php echo ( ($row-1) % 2) == 0 ? 'even' : 'odd' ?>">
                        <td><?php out::H($row) ?></td>
                        <td><a href="<?php out::H($link_url) ?>" title="View reports with this crasher."><?php out::H($crasher->signature) ?></a></td>
                        <td><?php out::H($crasher->build) ?></td>
                        <td><?php out::H($crasher->total) ?></td>
                        <td><?php out::H($crasher->win) ?></td>
                        <td><?php out::H($crasher->linux) ?></td>
                        <td><?php out::H($crasher->mac) ?></td>
                        <?php $row+=1 ?>
                    </tr>
                <?php endforeach ?>
            </tbody>
        </table>
    </div>
<?php endif ?>
