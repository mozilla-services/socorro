<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<div id="correlation" class="ui-tabs-hide"><h2>Correlations for <?= $current_product . ' ' . $current_version . ' ' . $current_os ?></h2>
	<p>Below are tables of correlation data generated by <a href="http://dbaron.org/mozilla/topcrash-modules">dbaron's scripts</a>. If this crash signature is
a top crasher, then we should be able to load it from <a href="<?= Kohana::config('correlation.path') ?>">the original text files</a>. Only the first <?= Kohana::config('correlation.max_file_size') ?>MB of each Platform's output is loaded. If this screen has data from multiple product/version/platforms, the crashiest was picked (<?= $current_product . ' ' . $current_version . ' ' . $current_os ?>).</p>
	<ul>
            <li id="mod"><h3>Modules <a href="#modver" title="Skip Down to Module Versions">Next</a></h3>
	<div id="module_correlation">Loading <?= html::image( array('src' => 'img/loading.png', 'width' => '16', 'height' => '17' )) ?></div></li>

            <li id="modver"><h3>Modules by versions <a href="#add" title="Skip Down to Add-ons">Next</a>
                <a href="#mod" title="Skip Up to Modules">Previous</a></h3>
                <div id="moduleversion-panel"><button name="moduleversion" class="load-version-data">Load</button></div></li>

            <li id="add"><h3>Add-ons <a href="#addver" title="Skip Down to Add-on Versions">Next</a>
                           <a href="#modver" title="Skip Up to Module Versions">Previous</a></h3>
	<div id="addon_correlation">Loading <?= html::image( array('src' => 'img/loading.png', 'width' => '16', 'height' => '17' )) ?></div></li>

            <li id="addver"><h3>Add-ons by versions <a href="#cpu" title="Skip Down to CPU Cores">Next</a>
                                       <a href="#add" title="Skip Up to Add-ons">Previous</a></h3>
                <div id="addonversion-panel"><button name="addonversion" class="load-version-data">Load</button></div></li>

            <li id="cpu"><h3>CPU Cores <a href="#addver" title="Skip Up to Add-on Versions">Previous</a></h3>
	<div id="cpu_correlation">Loading <?= html::image( array('src' => 'img/loading.png', 'width' => '16', 'height' => '17' )) ?></div></li>
        </ul>
        </div><!-- /correlation -->

<?php
// JavaScript uses these values for slurping in Correlation reports
$url_path = '/' . join('/',
		       array_map('rawurlencode',
				 array($current_product, $current_version, $current_os, $current_signature))) . '/';
?>
  <script type="text/javascript">//<![CDATA[
      var SocReport = {
          base: '<?= url::site('/correlation/ajax')?>/',
	  path: '<?= $url_path ?>',
	  loading: 'Loading <?= html::image( array('src' => 'img/loading.png', 'width' => '16', 'height' => '17')) ?>'
      };
//]]></script>
