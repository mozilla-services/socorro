<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html lang="en" dir="ltr" xmlns="http://www.w3.org/1999/xhtml">

    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <link href="<?php echo url::base() ?>css/screen.css" rel="stylesheet" type="text/css" media="screen" />
        <link href="<?php echo url::base() ?>favicon.ico" rel="icon" type="image/png" />
        <?php echo html::script(array('js/__utm.js',
                                      'js/jquery/jquery-1.3.2.min.js',
                                      'js/jquery/plugins/superfish-1.4.8.js',
                                      'js/socorro/nav.js'
                                )); ?>

        <?php slot::output('head') ?>

    </head>

    <body>
        <div id="page">
            <div id="header">	        
                <h1 id="logo"><a href="<?php echo url::base() ?>"><img
	           src="<?php echo url::base() ?>img/slate/mozillalogo.png"
	             width="200" height="33" alt="Mozilla" /></a></h1>
                <ul id="dev-links">
                    <li class="current"><a href="#" id="subnavtoggle"><img
		            src="<?php echo url::base() ?>img/slate/moz-developer.png"
		              width="124" height="32" alt="Moz Developer" /></a>
                        <ul id="subnav">
                            <li><a href="https://bugzilla.mozilla.org/" title="Bugzilla">Bugzilla</a></li>
                            <li><a href="http://tinderbox.mozilla.org/" title="Tinderbox">Tinderbox</a></li>
                            <li><a href="https://developer.mozilla.org/" title="MDC">Mozilla Developer Central</a></li>
                            <li><a href="http://mxr.mozilla.org/">Source Code Cross-reference</a></li>
                            </ul>
                    </li>
                </ul> <!-- /DEV-LINKS -->
		<h4>Quick Links</h4>
		<ul id="product-nav">
		<?php

		  foreach ($common_products as $prod => $releases) { ?>
		    <li class="product"><?= $prod ?>
		      <ol>
			<li class="product-nav-all-versions">All Versions</li>
	                <?php
			    foreach ($releases as $release => $version) { ?>
			        <li><a href="<?= url::base()?>query/query?do_query=1&amp;product=<?= urlencode($prod) ?>&amp;version=<?= urlencode($prod . ':' . $version) ?>"><?= $prod ?> <?= $version ?></a> <?= $release ?></li>
			<?php } ?>
		      

     			<li class="product-nav-other-versions">Other Versions &hellip;</li>
		      </ol>:
		      </li><!-- /product -->
		  <?php
		      
		  }
		  ?>
		      <li id="trend-nav"><ul>
			<!-- TODO Global current product / version -->
  		        <li id="topcrash-bysig" class="trend-report-link"><span class="label">Top Crashes: </span><a href="<?= url::base() ?>topcrasher/byversion/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>">By Signature</a></li>
     		        <li id="topcrash-byurl" class="trend-report-link"><span class="label">Top Crashes: </span><a href="<?= url::base() ?>topcrasher/byurl/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>">By URL</a></li>
      		        <li id="mtbf" class="trend-report-link"><a href="<?= url::base() ?>mtbf/of/<?= $chosen_version['product'] ?>/<?= $chosen_version['release'] ?>">MTBF</a></li>
			</ul></li>
		      <li id="adv-search-link"><a href="<?= url::base() ?>query/query">Advanced Search</a> or</li>
		      <li><form id="simple-search" method="get" action="<?= url::base() ?>query/simple"><fieldset><input type="text" name="q" value="Crash ID or Signature" /><input type="submit" /></fieldset></form></li>
		</ul>
            </div> <!-- /HEADER -->
      
        <div id="mainbody">
	  <div id="vertical-furniture"></div>
  	  <?php echo $content ?></div>

        </div> <!-- /PAGE -->
	
        <div id="footer">
	    <div id="footer-links">
            <ul>
                <li><a href="<?php echo url::base() ?>status?cache_bust=<?php echo time();?>">Server Status</a></li>
                <li><a href="http://code.google.com/p/socorro/">Project Info</a></li>
                <li><a href="http://code.google.com/p/socorro/source">Get the Source</a></li>
                <li><a href="http://wiki.mozilla.org/Breakpad">Breakpad Wiki</a></li>
            </ul>
	    </div>
        </div><!-- /FOOTER -->

    </body>
</html>
