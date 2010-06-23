<!DOCTYPE html>
<html class="production">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <link href="<?php echo url::base() ?>css/screen.css?v=1.8" rel="stylesheet" type="text/css" media="screen" />
    <link href="<?php echo url::base() ?>favicon.ico" rel="icon" type="image/png" />
    <?php 
    	echo html::script(
    	    array(
    	        'js/__utm.js',
                'js/jquery/jquery-1.3.2.min.js',
                'js/jquery/plugins/jquery.cookies.2.2.0.js',
                'js/socorro/nav.js?v=1.8'
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

        <form method="get" action="<?= url::base() ?>query/simple">
            <input type="text" id="q" name="q" value="Find Crash ID or Signature" />
            <input type="submit" class="hidden" />
        </form>
    </div>


	<h1>Product Navigation</h1>	

	<div class="version-nav">

		<input type="hidden" id="url_base" name="url_base" value="<?php if (isset($url_nav)) out::H($url_nav); else out::H(url::site()); ?>" />
		<input type="hidden" id="url_site" name="url_site" value="<?php out::H(url::site()); ?>" />

		<ul class="filter">
    		<li>
			Product:
			<select id="products_select">
			<?php foreach ($common_products as $product => $versions) { ?>
				<option <?php if ($product == $chosen_version['product']) echo 'SELECTED'; ?> value="<?php out::H($product); ?>"><?php out::H($product); ?></option>
			<?php } ?>
			</select>
			</li>
		
			<select id="product_version_select">
				<optgroup>
					<option value="Current Versions">Current Versions</option>
				</optgroup>
				<optgroup>
					<?php 
						foreach ($common_products as $product => $versions) {
							if ($chosen_version['product'] == $product) { 
	                        	$releases = array('Dev', 'Major', 'Release'); 
	                        	foreach ($versions as $version) { 
                    ?>
							<option value="<?php out::H($version); ?>"
								<?php if ($version == $chosen_version['version']) echo 'SELECTED'; ?>
							><?php out::H($version); ?></option>
                    <?php 
								}
							} 
						}
					?>
				</optgroup>
				<optgroup>
					<?php
						krsort($current_product_versions);					
						foreach ($current_product_versions as $version) { 
                        	if (
								$version->product == $chosen_version['product'] &&
								!in_array($version->version, $common_products[$version->product])
							) {
					?>
                            	<option value="<?php out::H($version->version); ?>"
                            	    <?php if ($version->version == $chosen_version['version']) echo ' SELECTED'; ?>
                            	><?php out::H($version->version); ?></option>
					<?php 
							}
 						}
					?>
				</optgroup>
			</select>
		
            <li>
                <label>Report:</label>
                <select id="report_select">
                    <optgroup>
                        <option <?php if (isset($nav_selection) && $nav_selection == 'overview') echo 'selected'; ?> 
							value="<?= url::base() ?>products/<?= $chosen_version['product'] ?><?php if (isset($chosen_version['version']) && !empty($chosen_version['version'])) echo '/versions/'.html::specialchars($chosen_version['version']); ?>">Overview</option>
                    </optgroup>
                    <optgroup>
                        <option <?php if (isset($nav_selection) && $nav_selection == 'crashes_user') echo 'selected'; ?>
							value="<?= url::base() ?>daily?p=<?= $chosen_version['product'] ?>&v[]=<?= $chosen_version['version'] ?>">Crashes per User</option>
                        <option <?php if (isset($nav_selection) && $nav_selection == 'nightlies') echo 'selected'; ?>
							value="<?= url::base() ?>products/<?= $chosen_version['product'] ?><?php if (isset($chosen_version['version']) && !empty($chosen_version['version'])) echo '/versions/'.html::specialchars($chosen_version['version']); ?>/builds">Nightly Builds</option>
                    </optgroup>
                    <optgroup>	
                        <option <?php if (isset($nav_selection) && $nav_selection == 'top_crashes') echo 'selected'; ?>
                            value="<?= url::base() ?>topcrasher/byversion/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>">Top Crashers</option>
                        <option <?php if (isset($nav_selection) && $nav_selection == 'top_url') echo 'selected'; ?> 
                            value="<?= url::base() ?>topcrasher/byurl/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>">Top Crashers by URL</option>
                        <option <?php if (isset($nav_selection) && $nav_selection == 'top_domain') echo 'selected'; ?> 
                            value="<?= url::base() ?>topcrasher/bydomain/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>">Top Crashers by Domain</option>
                        <option <?php if (isset($nav_selection) && $nav_selection == 'top_topsite') echo 'selected'; ?> 
                            value="<?= url::base() ?>topcrasher/bytopsite/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>">Top Crashers by Topsite</option>  
                    </optgroup>
				</select>
            </li>
		
		</ul>

		<div class="search">
			<a href="<?php out::H(url::site()); ?>query">Advanced Search</a>
		</div>
	</div>

      
    <div id="mainbody">
      	<?php echo client::messageFetchHtml(); // Status and Error messages for user ?>
    	<?php echo $content; ?>
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
    		</ul>
    	</div>


    	<div class="login">
            <?php if( $auth_is_active && Auth::instance()->logged_in() ) {?>
                <li><a><?php echo html::specialchars(Auth::instance()->get_user()); ?></a></li>
                <li><a href="<?php echo url::site(); ?>admin">Admin</a></li>
                <li><a href="<?= url::site('auth/logout', Kohana::config('auth.proto')) ?>">Log Out</a></li>
            <?php } elseif ($auth_is_active == FALSE) { ?>
                <li><a>Auth Disabled</a></li>
            <?php } else { ?>
                <li><a href="<?= url::site('auth/login', Kohana::config('auth.proto')) ?>">Log In</a></li>
            <?php } ?>
    	</div>
    </div>

</body>
</html>
