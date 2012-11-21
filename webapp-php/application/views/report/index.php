<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<?php slot::start('head') ?>
<?php /* Bug#530306 - don't reformat the [@ signature ] part below, it affects
                      our Bugzilla integration. No really. */ ?>
<title><?php if (! empty($report->signature)) { echo '[@ '; out::H($report->signature); echo '] - ';} ?> <?php out::H($report->product) ?> <?php out::H($report->version) ?> Crash Report - Report ID: <?php out::H($report->uuid) ?></title>

    <link rel='alternate' type='application/json' href='<?php echo $reportJsonZUri ?>' />

    <?php echo html::stylesheet(array(
        'css/flora/flora.all.css'
    ), 'screen')?>

    <?php echo html::script(array(
        'js/jquery/plugins/ui/jquery.ui.all.js',
        'js/jquery/plugins/ui/jquery.tablesorter.min.js',
        'js/socorro/bugzilla.js'
    ))?>



<?php slot::end() ?>


<div class="page-heading">
	<h2><?php out::H($report->product) ?> <?php out::H($report->version) ?> Crash Report <?php
    if (! empty($report->signature)) {?>
        [@ <?php out::H($report->signature) ?> ]
    <?php }?></h2>
</div>


<div class="panel">
    <div class="body notitle">

<div id="sumo-link"><?php
if (isset($report->sumo_signature) && !empty($report->signature)) { ?>
<a href="http://support.mozilla.com/search?q=<?=urlencode($report->sumo_signature) ?>" title="Find more answers at support.mozilla.com!">Search Mozilla Support for Help</a>
<?php } else { ?>
<a href="http://support.mozilla.com">Visit Mozilla Support for Help</a>
<?php } ?></div>

<?php if (array_key_exists('hangtype', $oopp_details)) { ?>
      <div class="oopp-hang"><div class="current">Lorentz Hang Minidump <span class="type">(<?= $oopp_details['hangtype'] ?>)</div>
	  <div class="pair"><?php if (array_key_exists('pair_error', $oopp_details)) { ?>
                                <?= $oopp_details['pair_error'] ?>
                            <?php } elseif (array_key_exists('pair_label', $oopp_details) &&
                                            array_key_exists('other_uuid', $oopp_details)) { ?>
	                        <?= $oopp_details['pair_label'] ?> Report: <a href="<?= $oopp_details['other_uuid'] ?>"><?= $oopp_details['other_uuid'] ?></a>
	                    <?php } ?>
          </div>
      </div><!-- /oopp-hang -->
<?php } ?>

<div id="report-header-details">ID: <span><?php out::H($report->uuid) ?></span><br/> Signature: <span><?php out::H($report->{'display_signature'}) ?></span>
<?php if(isset($report->duplicate_of)): ?>

<br />Duplicate Of: <span><a href="/report/index/<?php out::H($report->duplicate_of) ?>"><?php out::H($report->duplicate_of); ?></a></span>

<?php endif; ?>
</div>
<div id="report-index" class="flora">

    <ul class="ui-tabs-nav">
        <li><a href="#details"><span>Details</span></a></li>
        <li><a href="#modules"><span>Modules</span></a></li>
        <li><a href="#rawdump"><span>Raw Dump</span></a></li>
        <li><a href="#extensions"><span>Extensions</span></a></li>
        <li><a href="#comments"><span>Comments</span></a></li>
        <li><a href="#correlation"><span>Correlations</span></a></li>
    </ul>

    <div id="details">
        <table class="record data-table vertical">
            <tbody>
            <tr>
<th>Signature</th>
<td><?php out::H($report->signature) ?> 
  <a href="/report/list?signature=<?php echo urlencode($report->signature) ?>" class="sig-overview" title="View more reports of this type">More Reports</a> 
  <a href="/query?advanced=1&amp;signature=<?php echo urlencode($report->signature) ?>" class="sig-search" title="Search for more reports of this type">Search</a>
</td>
            </tr>
            <tr>
                <th>UUID</th><td><?php out::H($report->uuid) ?></td>
            </tr>
            <tr>
              <th>Date Processed</th><td><?php 
                $date = new DateTime($report->date_processed); 
                out::H($date->format('Y-m-d H:i:s')); ?></td>
            </tr>
<?php if (property_exists($report, 'processType')) { ?>
            <tr><th>Process Type</th><td><?= out::H($report->processType) ?>
    <?php if (property_exists($report, 'pluginName')) { ?>
	    <strong class="name"><?= out::H($report->pluginName) ?></strong>
    <?php } ?>
    <?php if (property_exists($report, 'pluginVersion')) { ?>
	    <span>Version:</span><span class="version"><?= out::H($report->pluginVersion) ?></span>
    <?php } ?>
    <?php if (property_exists($report, 'pluginFilename')) { ?>
            <span>Filename:</span> <span class="filename"><?= out::H($report->pluginFilename) ?></span>
    <?php } ?>
                </td></tr>
<?php } ?>

            <tr>
                <th>Uptime</th><td><?php out::H($report->uptime); ?></td>
            </tr>

            <?php if ($report->last_crash): ?>
            <tr>
                <th>Last Crash</th><td><?php
		     $seconds_in_words = TimeUtil::time_ago_in_words($report->last_crash);
                     ?><?= $seconds_in_words ?> before submission</td>
            </tr>
            <?php endif; ?>
            <?php if (property_exists($report, 'install_age')): ?>
            <tr>
                <th>Install Age</th><td><?php
                    $seconds_in_words = TimeUtil::time_ago_in_words($report->install_age); ?>
                    <?= $seconds_in_words ?>
                    since version was first installed.</td>
            </tr>
            <?php endif; ?>
            <tr>
                <th>Install Time</th><td><?php if (isset($report->install_time)) out::H(date("Y-m-d H:i:s", $report->install_time)); ?></td>
            </tr>
            <tr>
                <th>Product</th><td><?php out::H($report->product) ?></td>
            </tr>
            <tr>
                <th>Version</th><td><?php out::H($report->version) ?></td>
            </tr>
            <tr>
                <th>Build ID</th><td><?php out::H($report->build) ?></td>
            </tr>
            <tr>
                <th>Release Channel</th><td><?php out::H($report->ReleaseChannel) ?></td>
            </tr>
            <?php if ($branch && !empty($branch->branch)): ?>
            <tr>
                <th>Branch</th><td><?php out::H($branch->branch) ?></td>
            </tr>
            <?php endif; ?>
            <tr>
                <th>OS</th><td><?php out::H($report->os_name) ?></td>
            </tr>
            <tr>
                <th>OS Version</th><td><?php out::H($report->os_version) ?></td>
            </tr>
            <tr>
                <th>Build Architecture</th><td><?php out::H($report->cpu_name) ?></td>
            </tr>
            <tr>
                <th>Build Architecture Info</th><td><?php out::H($report->cpu_info) ?></td>
            </tr>
            <tr>
                <th>Crash Reason</th><td><?php out::H($report->reason) ?></td>
            </tr>
            <tr>
                <th>Crash Address</th><td><?php out::H($report->address) ?></td>
            </tr>
<?php if ($logged_in === TRUE) { ?>
	    <tr>
	  <th>Email Address</th><td>
	  <?php if(property_exists($report, 'email') && ! empty($report->email)){?>
               <a href="mailto:<? out::H($report->email) ?>"><? out::H($report->email) ?></a> - Super Sensitive! Don't mess around!
<?php } ?></td>
	    </tr>
            <tr>
	  <th>URL</th><td>
	  <?php if(property_exists($report, 'url') && ! empty($report->url)){?>
               <a href="<? out::H($report->url) ?>"><? out::H($report->url) ?></a> - Super Sensitive! Don't mess around!
<?php } ?></td>
	    </tr>
            <tr>
              <th>Exploitability</th>
                <td>
                  <?php if(property_exists($report, 'exploitability') && ! empty($report->exploitability)) {
                          out::H($report->exploitability) ?> - Super Sensitive! Don't mess around! <?php } ?>
                </td>
            </tr>
<?php } ?>
            <tr>
	    <th>User Comments</th><td><?php echo out::H($report->user_comments) ?></td>
            </tr>
<?php if (isset($report->app_notes)) { ?>
            <tr>
	    <th title="Notes added by the application's code during crash">App Notes</th>
            <td><pre><?php echo nl2br( out::H($report->app_notes
, FALSE))  ?></pre></td>
            </tr>
<?php } ?>
<?php if (isset($report->processor_notes)) { ?>
            <tr>
	    <th title="Notes added by Socorro when accepting the crash report">Processor Notes</th>
                             <td><?php echo nl2br( out::H($report->processor_notes, FALSE))  ?></td>
            </tr>
<?php } ?>
<?php if (isset($report->distributor)) { ?>
            <tr>
	    <th>Distributor</th><td><?php out::H($report->distributor) ?></td>
            </tr>
<?php } ?>
<?php if (isset($report->distributor_version)) { ?>
            <tr>
	    <th>Distributor Version</th><td><?php out::H($report->distributor_version) ?></td>
            </tr>
<?php } ?>
<?php if (property_exists($report, 'addons_checked')) { ?>
            <tr>
	    <th>EMCheckCompatibility</th><td><?php if ($report->addons_checked) { echo 'True'; } else { echo 'False'; } ?></td>
            </tr>
<?php } ?>
        <tr><th>Winsock LSP</th><td><pre><?php if (isset($report->Winsock_LSP)) nl2br(out::H($report->Winsock_LSP)) ?></pre></td></tr>
        <tr><th>Adapter Vendor ID</th><td><?php if (isset($report->AdapterVendorID)) out::H($report->AdapterVendorID) ?></td></tr>
        <tr><th>Adapter Device ID</th><td><?php if (isset($report->AdapterDeviceID)) out::H($report->AdapterDeviceID) ?></td></tr>
<?php if (property_exists($report, 'JavaStackTrace')) { ?>
            <tr>
	    <th>Java Stack Trace</th><td><pre><?php out::H($report->JavaStackTrace) ?></pre></td>
            </tr>
<?php } ?>
<?php if (property_exists($report, 'TotalVirtualMemory')) { ?>
        <tr><th>Total Virtual Memory</th><td><?php out::H($report->TotalVirtualMemory) ?></td></tr>
<?php } ?>
<?php if (property_exists($report, 'AvailableVirtualMemory')) { ?>
        <tr><th>Available Virtual Memory</th><td><?php out::H($report->AvailableVirtualMemory) ?></td></tr>
<?php } ?>
<?php if (property_exists($report, 'SystemMemoryUsePercentage')) { ?>
        <tr><th>System Memory Use Percentage</th><td><?php out::H($report->SystemMemoryUsePercentage) ?></td></tr>
<?php } ?>
<?php if (property_exists($report, 'AvailablePageFile')) { ?>
        <tr><th>Available Page File</th><td><?php out::H($report->AvailablePageFile) ?></td></tr>
<?php } ?>
<?php if (property_exists($report, 'AvailablePhysicalMemory')) { ?>
        <tr><th>Available Physical Memory</th><td><?php out::H($report->AvailablePhysicalMemory) ?></td></tr>
<?php } ?>
<?php if (property_exists($report, 'OOMAllocationSize')) { ?>
        <tr><th>OOMAllocationSize</th><td><?php out::H($report->OOMAllocationSize) ?></td></tr>
<?php } ?>
<?php if (property_exists($report, 'FlashProcessDump')) { ?>
        <tr><th>FlashProcessDump</th><td><?php out::H($report->FlashProcessDump) ?></td></tr>
<?php } ?>
<?php if (property_exists($report, 'Accessibility')) { ?>
        <tr><th>Accessibility</th><td><?php out::H($report->Accessibility) ?></td></tr>
<?php } ?>
<?php if (property_exists($report, 'Android_Manufacturer') && property_exists($report, 'Android_Model')) { ?>
        <tr><th>Device</th><td><?php out::H($report->Android_Manufacturer . " " . $report->Android_Model) ?></td></tr>
<?php } ?>
<?php if (property_exists($report, 'Android_Version')) { ?>
        <tr><th>Android API Version</th><td><?php out::H($report->Android_Version) ?></td></tr>
<?php } ?>
<?php if (property_exists($report, 'Android_CPU_ABI')) { ?>
        <tr><th>Android CPU ABI</th><td><?php out::H($report->Android_CPU_ABI) ?></td></tr>
<?php } ?>
            </tbody>
        </table>


        <div id="bugzilla" class="bugreporter">
            <p><strong>Bugzilla</strong>
            <?php if (isset($report_bug_url)) { ?>
                - Report this bug 
                <?php if (isset($report->product) && !empty($report->product)) { ?>
                    in <a href="<?= $current_product_bug_url ?>" target="_NEW"><?php trim(out::H($report->product)); ?></a>, 
                <?php } ?>
                <a href="<?= $report_bug_url . '&amp;product=Core' ?>" title="submit this bug in Core" target="_NEW"> Core</a>, 
                <a href="<?= $report_bug_url . '&amp;product=Plugins' ?>" title="submit this bug in Plugins" target="_NEW">Plug-Ins, </a> or 
                <a href="<?= $report_bug_url . '&amp;product=Toolkit' ?>" title="submit this bug in Toolkit" target="_NEW">Toolkit</a>
            <?php } ?>
            </p>

          <?php if (array_key_exists($report->signature, $sig2bugs)) { ?>
          <h2>Related Bugs</h2>
          <?php View::factory('common/list_bugs', array(
               'signature' => $report->signature,
                       'bugs' => $sig2bugs[$report->signature],
                       'mode' => 'full',
                       'suppressHeader' => TRUE
            ))->render(TRUE); ?>
          <?php } ?>
        </div><!-- /bugzilla -->

      <div id="frames">
    <?php if (isset($report->threads) && count($report->threads)): ?>

            <?php function stack_trace($frames, $truncated) { 
                $highlight = FALSE;
            ?>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Frame</th>
                            <th>Module</th>
                            <th class="signature-column">Signature</th>
                            <th>Source</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php $row = 1;
                            foreach ($frames as $frame): 
                                if($truncated) {
                                    $current_frame_number = $frame['frame_num'];
                                    $previous_frame_number = $frames[($row > 1 ? $row - 2 : 0)]['frame_num'];
                                    //if there is not a next element in the array set $next_frame_number == $current_frame_number
                                    //to avoid incorrect highlighting and invalid offset.
                                    $next_frame_number = (sizeof($frames) >= $row + 1) ? $frames[$row]['frame_num'] : $current_frame_number;
                                    if (($current_frame_number - $previous_frame_number) > 1 || ($next_frame_number - $current_frame_number) > 1) {
                                        $highlight = TRUE;
                                    } else {
                                        $highlight = FALSE;
                                    }
                                }
                        ?>
                        <tr <?php if ($highlight) {?>class="truncated-frame" title="Some frames have been removed as the automatic truncation routine was invoked."<?php } ?>>
                            <td><?php out::H($frame['frame_num']) ?></td>
                            <td><?php out::H($frame['module_name']) ?></td>
                            <?php
                                //often even the short signtaure is as long as 200+ characters, breaking the
                                //layout. Here we simply ensure this never happens.
                                if (strlen($frame['short_signature']) > 80) {
                                    $frame['short_signature'] = substr($frame['short_signature'], 0, 80);
                                }
                            ?>
                            <td title="<?php out::H($frame['signature']) ?>"><?php out::H($frame['short_signature']) ?></td>
                            <td>
                                <?php if ($frame['source_link']): ?>
                                    <a href="<?php out::H($frame['source_link']) ?>"><?php out::H($frame['source_info']) ?></a>
                                <?php else: ?>
                                    <?php out::H(stripslashes($frame['source_info'])) ?>
                                <?php endif ?>
                            </td>
                        </tr>
                        <?php
                            $row += 1;
                            endforeach 
                        ?>
                    </tbody>
                </table>
            <?php } ?>

            <h2>Crashing Thread</h2>
            <?php 
            /* First ensure that a crashing thread was identified by testing that $report->crashed_thread is not -1 */
            if ($report->crashed_thread != -1) {
                if (isset($report->threads) && count($report->threads) > $report->crashed_thread ) {
                    stack_trace( $report->threads[$report->crashed_thread], $is_truncated );
                }
            } else { ?>
                <p>No crashing thread identified.</p>
            <?php } ?>

            <p id="showallthreads" class="hidden"><a href="#allthreads">Show/hide other threads</a></p>
            <div id="allthreads">
                <?php for ($i=0; $i<count($report->threads); $i++): ?>
                    <?php if ($i == $report->crashed_thread) continue; ?>
                    <h2>Thread <?php out::H($i) ?></h2>
                    <?php stack_trace($report->threads[$i], FALSE) ?>
                <?php endfor ?>
            </div>

        <?php endif ?>
      </div><!-- /frames -->
    </div><!-- /details -->


    <div id="modules" class="ui-tabs-hide">
        <?php if (count($report->modules)): ?>
        <table class="tablesorter data-table" id="modules-list">
	<thead>
            <tr>
                <th>Filename</th>
                <th>Version</th>
                <th>Debug Identifier</th>
                <th>Debug Filename</th>
            </tr>
	</thead>
	<tbody>
            <?php $row = 1 ?>
            <?php foreach ($report->modules as $module): ?>
                <tr>
                    <td><?php out::H($module['filename']) ?></td>
                    <td><?php out::H($module['module_version']) ?></td>
                    <td><?php out::H($module['debug_id']) ?></td>
                    <td><?php out::H($module['debug_filename']) ?></td>
                </tr>
                <?php $row += 1 ?>
            <?php endforeach ?>
	</tbody>
        </table>
    <?php endif ?>
    </div><!-- /modules -->


    <div id="rawdump" class="ui-tabs-hide">
        <div class="code"><?php out::H($report->dump) ?></div>

		<?php if ($logged_in && !empty($raw_dump_urls)) { ?>
			<h3>Download the Raw Dump</h3>
			<?php foreach ($raw_dump_urls as $url) { ?>
				<p><a href="<?php out::H($url); ?>"><?php out::H($url); ?></a></p>
			<?php } ?>
		<?php } ?>
    </div><!-- /rawdump -->


    <div id="extensions" class="ui-tabs-hide">
        <?php if (!empty($extensions)) { ?>
	        <table class="data-table">
	            <thead>
	            <tr>
					<th>Extension</th>
	                <th>Extension Id</th>
	                <th>Version</th>
					<th>Current?</th>
	            </tr>
	            </thead>
	            <tbody>
	            <?php $row = 1 ?>
	            <?php foreach ($extensions as $extension) { ?>
	                <tr>
	                    <td><a href="<?php out::H($extension['link']) ?>"><?php out::H($extension['name']) ?></a></td>
	                    <td><?php if (isset($extension['extension_id'])) out::H($extension['extension_id']) ?></td>
	                    <td><?php if (isset($extension['extension_version']))  out::H($extension['extension_version']) ?></td>
						<td><?php
								if (isset($extension['extension_version']) && isset($extension['latest_version'])) {
									if ($extension['extension_version'] !== $extension['latest_version']) {
							?>
									<strong><?php out::H($extension['latest_version']); ?></strong>
							<?php } else { ?>
									current
								<?php } ?>
							<?php } ?>
						</td>
					<?php $row += 1; ?>
					</tr>
	            <?php } ?>
	            </tbody>
	        </table>
		<?php } else { ?>
			<p><em>No extensions were installed.</em></p>
		<?php } ?>
    </div><!-- /extensions -->
<?php View::factory('common/comments')->render(TRUE); ?>

    <?php View::factory('common/correlation', array(
			    'current_signature' => $report->signature,
			    'current_product'   => $report->product,
			    'current_version'   => $report->version,
			    'current_os'        => $report->os_name))->render(TRUE); ?>

</div> <!-- /report-index -->


    </div>
</div>


    <?php echo html::script(
	array(
	    'js/socorro/report.js',
	    'js/socorro/correlation.js'
	    ));
    ?>
