<!DOCTYPE html>
<html class="production">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <link href="<?php echo url::base() ?>css/screen.css?v=1.7.7" rel="stylesheet" type="text/css" media="screen" />
    <link href="<?php echo url::base() ?>favicon.ico" rel="icon" type="image/png" />
    <?php
    	echo html::script(
    	    array(
                'js/jquery/jquery-1.3.2.min.js',
                'js/jquery/plugins/jquery.cookies.2.2.0.js',
                'js/socorro/nav.js?v=1.7.6'
            )
        );
    ?>
</head>

<body>
    <div class="page-header">
    	<h1>
    		<a href="<?= url::site(); ?>">
    			<span class="icon"></span>
    			<span class="title">Mozilla Crash Reports</span>
    		</a>
    	</h1>
        <form method="get" action="<?= url::base() ?>query/query">
            <input type="hidden" name="query_type" value="simple" />
            <input type="hidden" name="do_query" value="1">
            <input type="text" id="q" name="query" value="Find Crash ID or Signature" />
            <input type="submit" class="hidden" />
        </form>
    </div>


	<h1>Product Navigation</h1>
	<div class="version-nav">
	    <input type="hidden" id="url_base" name="url_base" value="<?php echo url::base() ?>/products/Firefox" />
		<input type="hidden" id="url_site" name="url_site" value="<?php echo url::base() ?>" />
	    <ul class="filter">
    		<li>
                Product:
                <select id="products_select">
                    <option value="Firefox">Firefox</option>
                    <option value="Thunderbird">Thunderbird</option>
                    <option value="Camino">Camino</option>
                    <option value="SeaMonkey">SeaMonkey</option>
                    <option value="Fennec">Fennec</option>
                </select>
            </li>
		</ul>
		<div class="search">
			<a href="<?php out::H(url::site()); ?>query">Advanced Search</a>
		</div>
	</div>


    <?php
        $error_404 = (isset($trace) && strstr($trace, "show_404")) ? true : false;
        $title = ($error_404) ? "Page not Found" : "Error";
        $error_log = ($error_404) ? '[404 Page Not Found]' : '[5xx Error]';
        if (!empty($line) && !empty($file)) {
            $error_log .= ' File: ' . $file . '; Line: ' . $line . '; Message: ' . $message;
        }
        Kohana::log('error', $error_log);
    ?>

    <div id="mainbody">
	    <div class="page-heading">
	        <h2><?php echo html::specialchars($title); ?></h2>
	    </div>
	    <div class="panel">
	        <div class="body notitle">
            <?php if ($error_404) { ?>
                <p>The requested page could not be found.</p>
                <p>If you followed a dead link on the website, please
            <?php } else { ?>
                <p>Something bad happened.  It's not you, it's me.</p>
                <p>Please
            <?php } ?>
                submit a <a href="https://bugzilla.mozilla.org/enter_bug.cgi?product=Webtools&component=Socorro&bug_file_loc=<?php echo urlencode($_SERVER['SCRIPT_URI']); ?>">Bugzilla ticket</a> describing what happened, and please include the URL for this page.</p>
	        </div>
	    </div>
    </div>

    <div class="page-footer">
    	<div class="nav">
    		<div class="about">
    			<strong>Mozilla Crash Reports</strong> - Powered by <a href="http://code.google.com/p/socorro/">Socorro</a>
    		</div>
    		<ul>
                <li><a href="<?php echo url::base() ?>status">Server Status</a></li>
                <li><a href="http://code.google.com/p/socorro/">Project Info</a></li>
                <li><a href="http://code.google.com/p/socorro/source">Source Code</a></li>
                <li><a href="http://wiki.mozilla.org/Breakpad">Breakpad Wiki</a></li>
                <li><a href="http://www.mozilla.org/about/policies/privacy-policy.html">Privacy Policy</a></li>
    		</ul>
    	</div>
    </div>

</body>
</html>
