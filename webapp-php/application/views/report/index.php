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
if (is_null($report->signature) || empty($report->signature)) { ?>
<a href="http://support.mozilla.com">Visit Mozilla Support for Help</a>
<?php } else { ?>
<a href="http://support.mozilla.com/search?q=<?=urlencode($report->sumo_signature) ?>" title="Find more answers at support.mozilla.com!">Search Mozilla Support for Help</a>
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

<div id="report-header-details">ID: <span><?php out::H($report->uuid) ?></span><br/> Signature: <span><?php out::H($report->{'display_signature'}) ?></span></div>
<div id="report-index" class="flora">

    <ul>
        <li><a href="#details"><span>Details</span></a></li>
        <li><a href="#modules"><span>Modules</span></a></li>
        <li><a href="#rawdump"><span>Raw Dump</span></a></li>
        <li><a href="#extensions"><span>Extensions</span></a></li>
        <li><a href="#comments"><span>Comments</span></a></li>
        <li><a href="#correlation"><span>Correlations</span></a></li>
    </ul>
    <div id="details">
        <table class="list record">
            <tr>
<th>Signature</th><td><?php out::H($report->signature) ?></td>
            </tr>
            <tr>
                <th>UUID</th><td><?php out::H($report->uuid) ?></td>
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
                <th>Uptime</th><td><?php out::H(TimeUtil::ghetto_time_ago_in_words($report->uptime)); ?></td>
            </tr>

            <?php if ($report->last_crash): ?>
            <tr>
                <th>Last Crash</th><td><?php out::H($report->last_crash) ?> seconds <?php 
		     $seconds_in_words = TimeUtil::ghetto_time_ago_in_words($report->last_crash);
                     if (! empty($seconds_in_words)) { ?>(<?= $seconds_in_words ?>) <?php } ?> before submission</td>
            </tr>
            <?php endif; ?>
            <?php if (property_exists($report, 'install_age')): ?>
            <tr>
                <th>Install Age</th><td><?php out::H($report->install_age) ?> seconds <?php 
                    $seconds_in_words = TimeUtil::ghetto_time_ago_in_words($report->install_age);
                    if (! empty($seconds_in_words)) { ?>(<?= $seconds_in_words ?>) <?php } ?>
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
                <th>CPU</th><td><?php out::H($report->cpu_name) ?></td>
            </tr>
            <tr>
                <th>CPU Info</th><td><?php out::H($report->cpu_info) ?></td>
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
<?php } ?>

            <tr>
	    <th>User Comments</th><td><?php echo out::H($report->user_comments) ?></td>
            </tr>
<?php if (isset($report->app_notes)) { ?>
            <tr>
	    <th title="Notes added by the application's code during crash">App Notes</th>
            <td><?php echo nl2br( out::H($report->app_notes
, FALSE))  ?></td>
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
        <tr><th>Winsock LSP</th><td><?php if (isset($report->Winsock_LSP)) nl2br(out::H($report->Winsock_LSP)) ?></td></tr>
        <tr><th>Adapter Vendor ID</th><td><?php if (isset($report->AdapterVendorID)) out::H($report->AdapterVendorID) ?></td></tr>
        <tr><th>Adapter Device ID</th><td><?php if (isset($report->AdapterDeviceID)) out::H($report->AdapterDeviceID) ?></td></tr>
        </table>


        <div id="bugzilla">
            <h2>Bugzilla
            <?php if (isset($report_bug_url)) { ?>
                 - <a href="<?php out::H($report_bug_url); ?>" target="_NEW">Report this Crash</a>
            <?php } ?>
            </h2>
        
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
           
            <?php function stack_trace($frames) { ?>
                <table class="list">
                    <tr>
                        <th>Frame</th>
                        <th>Module</th>
                        <th class="signature-column">Signature</th>
                        <th>Source</th>
                    </tr>
                    <?php $row = 1 ?>
                    <?php foreach ($frames as $frame): ?>
                        <tr>
                            <td><?php out::H($frame['frame_num']) ?></td>
                            <td><?php out::H($frame['module_name']) ?></td>
                            <td title="<?php out::H($frame['signature']) ?>"><?php out::H($frame['short_signature']) ?></td>
                            <td>
                                <?php if ($frame['source_link']): ?>
                                    <a href="<?php out::H($frame['source_link']) ?>"><?php out::H($frame['source_info']) ?></a>
                                <?php else: ?>
                                    <?php out::H($frame['source_info']) ?>
                                <?php endif ?>
                            </td>
                        </tr>
                        <?php $row += 1 ?>
                    <?php endforeach ?>
                </table>
            <?php } ?>

            <h2>Crashing Thread</h2>
            <?php if (isset($report->threads) && count($report->threads) > $report->crashed_thread ){
                    stack_trace( $report->threads[$report->crashed_thread] );
                  } ?>    
               

            <p id="showallthreads" class="hidden"><a href="#allthreads">Show/hide other threads</a></p>
            <div id="allthreads">
                <?php for ($i=0; $i<count($report->threads); $i++): ?>
                    <?php if ($i == $report->crashed_thread) continue; ?>
                    <h2>Thread <?php out::H($i) ?></h2>
                    <?php stack_trace($report->threads[$i]) ?>
                <?php endfor ?>
            </div>

            <script type="text/javascript">document.getElementById("allthreads").style.display="none";</script>

        <?php endif ?>
      </div><!-- /frames -->
    </div><!-- /details -->


    <div id="modules">
        <?php if (count($report->modules)): ?>
        <table class="list" id="modules-list">
            <tr>
                <th>Filename</th>
                <th>Version</th>
                <th>Debug Identifier</th>
                <th>Debug Filename</th>
            </tr>
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
        </table>
    <?php endif ?>
    </div><!-- /modules -->


    <div id="rawdump">
        <div class="code"><?php out::H($report->dump) ?></div>

		<?php if ($logged_in && !empty($raw_dump_urls)) { ?>
			<h3>Download the Raw Dump</h3>
			<?php foreach ($raw_dump_urls as $url) { ?>
				<p><a href="<?php out::H($url); ?>"><?php out::H($url); ?></a></p>
			<?php } ?>
		<?php } ?>
    </div><!-- /rawdump -->


    <div id="extensions">
        <?php if (!empty($extensions)) { ?>
	        <table class="list">
	            <tr>
					<th>Extension</th>
	                <th>Extension Id</th>
	                <th>Version</th>
					<th>Current?</th>
	            </tr>
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
