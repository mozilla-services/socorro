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

        <div id="page-header">
        <div class="header-wrapper">
            <h1><a href="<?php echo url::base() ?>" title="Home">
                <span>Mozilla Crash Reports</span>
            </a></h1>
		<form id="simple-search" method="get" action="<?= url::base() ?>query/simple">
	            <fieldset>
                            <input type="text" name="q" value="Crash ID or Signature" />
                            <input type="submit" class="hidden" />
	            </fieldset>
                        </form>
               <ul id="top-nav" class="shortcuts">
                    <!-- li>Quick Links:</li -->
                    <?php
		      // TODO Kludgy, fix this duplicate code
                      foreach ($common_products as $prod => $releases) {
		          if ( $prod != "Firefox" && $prod != "Thunderbird") {
		              continue;
		          }
		      ?>
                        <li class="product dropdown"><strong><?= $prod ?> &#9662;</strong>
		          <div>
                          <ul class="product-versions">
                                <?php
                            foreach ($releases as $release => $version) { ?>
                                <li><a href="<?= url::base()?>query/query?do_query=1&amp;product=<?= urlencode($prod) ?>&amp;version=<?= urlencode($prod . ':' . $version) ?>"><span class="release-type"><?= ucwords($release) ?></span> (<span class="version"><?= $version ?></span>)</a></li>
                        <?php } ?>
				<li class="more"><a href="<?= url::base() ?>query/query?do_query=1&amp;product=<?= urlencode($prod) ?>">More Versions</a></li>
                          </ul><!-- /product-versions -->
			  </div>
                          </li><!-- /product -->

                      <?php
                      }
			  ?>
			  <li class="dropdown"><strong>More &#9662;</strong>
			  <div class="large">
	         <?php
                      foreach ($common_products as $prod => $releases) {
		          if ( $prod == "Firefox" || $prod == "Thunderbird") {
		              continue;
		          }
		      ?>
                          <ul class="xproduct-versions">
                            <li class="xproduct all"><strong><?= $prod ?></strong></li>
                                <?php
                            foreach ($releases as $release => $version) { ?>
                                <li><a href="<?= url::base()?>query/query?do_query=1&amp;product=<?= urlencode($prod) ?>&amp;version=<?= urlencode($prod . ':' . $version) ?>"
			               ><span class="release-type"><?= ucwords($release) ?></span> (<span class="xversion"><?= $version ?></span>)</a></li>
                        <?php } ?>
				  <li class="more"><a href="<?= url::base() ?>query/query?do_query=1&amp;product=<?= urlencode($prod) ?>">More Versions</a></li>
			   </ul><!-- /xproduct-versions -->		          

                     <?php
                      }			  
                      ?>

			 </div><!-- /large -->
                      </li><!-- /more -->
 		      <li class="separated"><strong>Trend Reports &#9662;</strong>
		        <div>
			  
<ul>
		        <li id="topcrash-bysig" class="trend-report-link"><a href="<?= url::base() ?>topcrasher/byversion/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>"
                                                                             >Top Crashes By Signature</a></li>
    		        <li id="topcrash-byurl" class="trend-report-link"><a href="<?= url::base() ?>topcrasher/byurl/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>"
			                                                     >Top Crashes By URL</a></li>
			<li id="topcrash-bydomain" class="trend-report-link"><a href="<?= url::base() ?>topcrasher/bydomain/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>"
									        >Top Crashes By Domain</a></li>
     		        <li id="mtbf" class="trend-report-link"><a href="<?= url::base() ?>mtbf/of/<?= $chosen_version['product'] ?>/<?= $chosen_version['release'] ?>">Mean Time Before FAIL</a></li>
		</ul>
    		        </div>

		      </li>
		      <li class="separated"><a href="<?= url::base() ?>query/query">Advanced Search</a></li>
                </ul>
	   </div><!-- /header-wrapper -->
          </div> <!-- /page-header -->
      
        <div id="mainbody">
 	  <?php echo $content ?>

        </div> <!-- /mainbody -->
	
        <div id="footer">
	    <div id="footer-links">
            <ul>
                <li><a href="<?php echo url::base() ?>status?cache_bust=<?php echo time();?>">Server Status</a></li>
                <li><a href="http://code.google.com/p/socorro/">Project Info</a></li>
                <li><a href="http://code.google.com/p/socorro/source">Get the Source</a></li>
                <li><a href="http://wiki.mozilla.org/Breakpad">Breakpad Wiki</a></li>
            </ul>
	    </div><!-- footer-links -->
       </div><!-- /FOOTER -->

    </body>
</html>
