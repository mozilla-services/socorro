<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<?php if (isset($reports) && !empty($reports)) { ?>
    <table id="signatureList" class="tablesorter data-table">
        <thead>
            <tr>
                <th>Rank</th>
                <th>Signature</th>
                <?php if ($showPluginName) { ?>
                    <th>Plugin Name/Ver</th>
                <?php } ?>
                <?php if ($showPluginFilename) { ?>
                    <th>Plugin Filename</th>
                <?php } ?>
                <?php if (count($platforms) > 1) { ?>
                    <th>#</th>
                <?php } ?>
                <?php foreach ($platforms as $platform) { ?>
                    <th><?php out::H(substr($platform->name, 0, 3)) ?></th>
                <?php } ?>
                <?php if (isset($sig2bugs)) { ?>
                    <th class="bugzilla_numbers">Bugzilla IDs</th>
                <?php } ?>
            </tr>
        </thead>
        <tbody>
            <?php
            $row = (isset($page) && isset($items_per_page) && $page > 1)
                    ? (1 + (($page-1) * $items_per_page)) : 1;
            foreach ($reports as $report) { ?>
                <tr>
                <td><?php out::H($row) ?></td>
                <td>
                    <?php
                    $url_params = $params;
                    if (property_exists($report, 'missing_sig_param')) {
                        $url_params['missing_sig'] = $report->{'missing_sig_param'};
                    } else {
                        $url_params['signature'] = $report->signature;
                    }
                    if (array_key_exists('build_id', $url_params)) {
                        $b = trim($url_params['build_id']);
                        if (empty($b)) {
                            unset($url_params['build_id']);
                        }
                    }
                    $url = url::base() . 'report/list?'
                        . html::query_string($url_params);
                    ?>
                    <a href="<?php echo $url ?>">
                        <?php out::H($report->{'display_signature'}) ?>
                    </a>
                    <?php
                    if ($report->{'display_null_sig_help'}) {
                        echo " <a href='http://code.google.com/p/socorro/wiki/"
                            . "NullOrEmptySignatures' class='inline-help'>"
                            . "Learn More</a> ";
                    } ?>
                    <div class="signature-icons">
                        <?php
                        View::factory('common/hang_details', array(
                            'crash' => $report->{'hang_details'}
                            ))->render(TRUE);
                        ?>
                    </div>
                </td>
                <?php if ($showPluginName) { ?>
                    <td>
                        <?php out::H($report->pluginname . ' '
                            . $report->pluginversion) ?>
                    </td>
                <?php } ?>
                <?php if ($showPluginFilename) { ?>
                  <td><?php out::H($report->pluginfilename) ?></td>
                <?php } ?>
                <?php if (count($platforms) > 1) { ?>
                    <td><?php out::H($report->count) ?></td>
                <?php } ?>
                <?php foreach ($platforms as $platform) { ?>
                    <td><?php out::H($report->{'is_'.$platform->id}) ?></td>
                <?php } ?>
                <?php if (isset($sig2bugs)) {?>
                    <td>
                    <?php
                    if (array_key_exists($report->signature, $sig2bugs)) {
                        $bugs = $sig2bugs[$report->signature];
                        for ($i = 0; $i < 3 and $i < count($bugs); $i++) {
                            $bug = $bugs[$i];
                            View::factory('common/bug_number')->set('bug',
                                $bug)->render(TRUE);
                        echo ", ";
                        } ?>
                        <div class="bug_ids_extra">
                            <?php
                            for ($i = 3; $i < count($bugs); $i++) {
                                $bug = $bugs[$i];
                                View::factory('common/bug_number')
                                    ->set('bug', $bug)
                                    ->render(TRUE);
                            } ?>
                        </div>
                        <?php if (count($bugs) > 0) { ?>
                            <a href='#'
                               title="Click to See all likely bug numbers"
                               class="bug_ids_more">More</a>
                            <?php
                            View::factory('common/list_bugs', array(
                                'signature' => $report->signature,
                                'bugs' => $bugs,
                                'mode' => 'popup'
                            ))->render(TRUE);
                        }
                    } ?>
                    </td>
                <?php } ?>
                </tr>
                <?php $row += 1 ?>
            <?php } ?>
        </tbody>
    </table>

    </div>
</div>

<?php } else { ?>

    <p>No results were found.</p>
    
    </div>
</div>

<?php } ?>
