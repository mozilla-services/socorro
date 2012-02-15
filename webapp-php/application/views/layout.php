<!DOCTYPE html>
<html class="production">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <link href="<?php echo url::base() ?>css/screen.css?v=1.7.6" rel="stylesheet" type="text/css" media="screen" />
    <link href="<?php echo url::base() ?>favicon.ico" rel="icon" type="image/png" />
    <?php
    	echo html::script(
    	    array(
                'js/jquery/jquery-1.6.4.min.js',
                'js/jquery/plugins/jquery.cookies.2.2.0.js',
                'js/socorro/nav.js?v=1.7.6'
            )
        ); // Global Javascript includes
    	if (isset($js)) echo $js; // Javascript includes from Controller
    	if (isset($css)) echo $css; // CSS includes from Controller
        slot::output('head');
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

        <form id="simple_search" method="get" action="<?= url::base() ?>query/query">
            <input type="hidden" name="query_type" value="simple" />
            <input type="hidden" name="do_query" value="1">
            <input type="text" id="q" name="query" value="Find Crash ID or Signature" />
            <input type="submit" class="hidden" />
        </form>
    </div>


	<h1>Product Navigation</h1>

	<div class="version-nav">

		<input type="hidden" id="url_base" name="url_base" value="<?php if (isset($url_nav)) out::H($url_nav); else if ($chosen_version['product']) out::H('/products/' . $chosen_version['product']); else out::H(url::site()); ?>" />
		<input type="hidden" id="url_site" name="url_site" value="<?php out::H(url::site()); ?>" />

		<ul class="filter">
    		<li>
			Product:
			<select id="products_select">
			<?php foreach ($current_products as $product) { ?>
				<option <?php if ($product == $chosen_version['product']) echo 'SELECTED'; ?> value="<?php out::H($product); ?>"><?php out::H($product); ?></option>
			<?php } ?>
			</select>
			</li>
			<li class="version_select">
			<select id="product_version_select" <?php if (isset($error) && $error == 1) echo 'disabled'?>>
				<optgroup label=" ">
					<option value="Current Versions">Current Versions</option>
				</optgroup>
                <?php if (isset($featured_versions) && !empty($featured_versions)) { ?>
				    <optgroup label=" ">
				    	<?php foreach ($featured_versions as $featured_version) { ?>
                            <option value="<?php out::H($featured_version->version); ?>"
                            	<?php if ($featured_version->version == $chosen_version['version']) echo 'SELECTED'; ?>
                            ><?php out::H($featured_version->version); ?></option>
                        <?php } ?>
				    </optgroup>
			    <?php } ?>
			    <?php if (isset($unfeatured_versions) && !empty($unfeatured_versions)) { ?>
				    <optgroup label=" ">
				    	<?php foreach ($unfeatured_versions as $unfeatured_version) { ?>
                            <option value="<?php out::H($unfeatured_version->version); ?>"
                            	<?php if ($unfeatured_version->version == $chosen_version['version']) echo 'SELECTED'; ?>
                            ><?php out::H($unfeatured_version->version); ?></option>
                        <?php } ?>
				    </optgroup>
				<?php } ?>
			</select>
			</li>
            <li>
                <label>Report:</label>
                <select id="report_select" <?php if (isset($error) && $error == 1) echo 'disabled'?>>
                    <optgroup label=" ">
                        <option <?php if (isset($nav_selection) && $nav_selection == 'overview') echo 'selected'; ?>
							value="<?= url::base() ?>products/<?= $chosen_version['product'] ?><?php if (isset($chosen_version['version']) && !empty($chosen_version['version'])) echo '/versions/'.html::specialchars($chosen_version['version']); ?>">Overview</option>
                    </optgroup>
                    <optgroup label=" ">
                        <option <?php if (isset($nav_selection) && $nav_selection == 'crashes_user') echo 'selected'; ?>
							value="<?= url::base() ?>daily?p=<?= $chosen_version['product'] ?>&amp;v[]=<?= $chosen_version['version'] ?>">Crashes per User</option>
                        <option <?php if (isset($nav_selection) && $nav_selection == 'nightlies') echo 'selected'; ?>
							value="<?= url::base() ?>products/<?= $chosen_version['product'] ?><?php if (isset($chosen_version['version']) && !empty($chosen_version['version'])) echo '/versions/'.html::specialchars($chosen_version['version']); ?>/builds">Nightly Builds</option>
                        <option <?php if (isset($nav_selection) && $nav_selection == 'hang_report') echo 'selected'; ?>
							value="<?= url::base() ?>hangreport/byversion/<?= $chosen_version['product'] ?>/<?php if (isset($chosen_version['version']) && !empty($chosen_version['version'])) echo html::specialchars($chosen_version['version']); ?>">Hang Report</option>
                    </optgroup>
                    <optgroup label=" ">
                        <option <?php if (isset($nav_selection) && $nav_selection == 'top_changers') echo 'selected'; ?>
                            value="<?= url::base() ?>products/<?= $chosen_version['product'] ?><?php if (isset($chosen_version['version']) && !empty($chosen_version['version'])) echo '/versions/'.html::specialchars($chosen_version['version']); ?>/topchangers">Top Changers</option>
                        <option <?php if (isset($nav_selection) && $nav_selection == 'top_crashes') echo 'selected'; ?>
                            value="<?= url::base() ?>topcrasher/byversion/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>">Top Crashers</option>
                    </optgroup>
				</select>
            </li>

		</ul>

		<div class="search">
			<a href="<?php out::H(url::site()); ?>query?advanced=1">Advanced Search</a>
		</div>
	</div>


    <div id="mainbody">
      	<?php echo client::messageFetchHtml(); // Status and Error messages for user ?>
    	<?php echo $content; ?>
    </div>


    <div class="page-footer">
    	<div class="nav">
    		<div class="about">
                <strong>Mozilla Crash Reports</strong> - Powered by <a href="https://github.com/mozilla/socorro">Socorro</a>
    		</div>

    		<ul>
                <li><a href="<?php echo url::base() ?>status">Server Status</a></li>
                <li><a href="http://socorro.readthedocs.org/">Project Info</a></li>
                <li><a href="https://github.com/mozilla/socorro">Source Code</a></li>
                <li><a href="http://wiki.mozilla.org/Breakpad">Breakpad Wiki</a></li>
                <li><a href="http://www.mozilla.org/about/policies/privacy-policy.html">Privacy Policy</a></li>
    		</ul>
    	</div>


    	<div class="login">
		<ul>
            <?php if( $auth_is_active && Auth::instance()->logged_in() ) {?>
                <li><a><?php echo html::specialchars(Auth::instance()->get_user()); ?></a></li>
                <li><a href="<?php echo url::site(); ?>admin">Admin</a></li>
                <li><a href="<?= url::site('auth/logout', Kohana::config('auth.proto')) ?>">Log Out</a></li>
            <?php } elseif ($auth_is_active == FALSE) { ?>
                <li><a href="<?php echo url::site(); ?>admin">Admin</a></li>
            <?php } else { ?>
                <li><a href="<?= url::site('auth/login', Kohana::config('auth.proto')) ?>">Log In</a></li>
            <?php } ?>
		</ul>
    	</div>
    </div>

</body>
</html>
