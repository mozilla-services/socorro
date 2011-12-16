
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
                <?php
                    foreach ($changers as $changer) {
            	        if (is_null($changer['signature'])) {
            			    $display_signature = Crash::$null_sig;
            		    } else if(empty($changer['signature'])) {
            			    $display_signature = Crash::$empty_sig;
            		    } else {
            			    $display_signature = $changer['signature'];
            		    }
                    ?>

                    <tr>
                        <td><div class="trend <?= $changer['trendClass'] ?>"><?= $changer['changeInRank']; ?></div></td>
                        <td><?= ($changer['currentRank']); ?></td>
                        <td><a class="signature" href="<?= ($changer['url']); ?>"
                           title="View reports with this crasher."><?php out::H($display_signature); ?></a>
                        </td>
                    </tr>
                <?php } ?>
            </table>
            <p><a href="<?php echo url::base() . $url_csv; ?>">Download CSV</a></p>
            <p><a href="<?php echo url::base() . $url_rss; ?>">Subscribe to RSS</a></p>
        </div>
    <?php } ?>
    <br class="clear">
    </div>
<?php } else { ?>
    <p>There were no top changers that matched the criteria you specified.</p>
<?php } ?>
