<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <link href="<?php echo url::base() ?>css/screen.css" rel="stylesheet" type="text/css" media="screen" />
    <link href="<?php echo url::base() ?>favicon.ico" rel="icon" type="image/png" />
    <?php 
    	echo html::script(
    	    array(
    	        'js/__utm.js',
                'js/jquery/jquery-1.3.2.min.js',
                'js/jquery/plugins/jquery.cookies.2.2.0.js',
                'js/socorro/nav.js'
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
    
    <div class="product-nav">
    	<ul>
        <?php foreach ($common_products as $product => $versions) { ?>
    		<li>
                <a href="<?php echo url::base() ?>products/<?php out::H($product); ?>" 
                    <?php 
                        if ($product == $chosen_version['product'] && !(isset($nav_selection) && $nav_selection == 'query')) { 
                            echo ' class="selected"'; 
                        } 
                    ?>
                ><span><?php out::H($product); ?></span></a>
                
                <?php if ($chosen_version['product'] != $product) { ?>
                <ul class="dropdown">
                    <?php 
                        $releases = array('Dev', 'Major', 'Release'); 
                        foreach ($versions as $version) { 
                    ?>

                       <li><a href="<?php echo url::base() ?>products/<?php out::H($product); ?>/versions/<?php out::H($version); ?>"><?php out::H($product); ?> <?php out::H($version); ?> <span><?php // out::H(array_shift($releases)); ?></span></a></li>
                    <?php } ?>
		            <li class="sep"></li>
		            <li><a href="<?php echo url::base() ?>products/<?php out::H($product); ?>"><?php out::H($product); ?> <span>All Versions</span></a></li>
			    </ul>
			    <?php } ?>
			    
			</li>
        <?php } ?>
        </ul>

        <ul class="search">
    		<li><a href="<?php echo url::base() ?>query"
                <?php 
                    if (isset($nav_selection) && $nav_selection == 'query') {
                        echo ' class="selected"'; 
                    }
                ?>
            >Advanced Search</a></li>
    	</ul>

    </div>


    <?php if (!isset($nav_selection) || (isset($nav_selection ) && $nav_selection != 'query')) { ?>
    <div class="version-nav">
        
        <?php foreach ($common_products as $product => $versions) { ?>
            <?php if ($product == $chosen_version['product']) { ?>
            	<div class="choices">
                    <input type="hidden" id="base_url" name="base_url" value="<?php if (isset($url_nav)) out::H($url_nav); else out::H(url::site()); ?>" />
        		    <div class="label">Version:</div>
                    <ul>
                        <li><a href="<?php echo url::base() ?>products/<?php out::H($product); ?>"
                            <?php if (empty($chosen_version['version'])) echo ' class="selected"'; ?>
                        >All</a></li>
                        
                        <?php foreach ($versions as $version) { ?>
                           <a href="<?php echo url::base() ?>products/<?php out::H($product); ?>/versions/<?php out::H($version); ?>"
                               <?php if ($version == $chosen_version['version']) echo ' class="selected"'; ?>
                           ><?php out::H($version); ?></a>
                        <?php } ?>
                        
                        <li><span class="more">
                            <select id="product_version" name="product_version">
                               <option>More Versions</option>
                                <?php foreach ($current_product_versions as $version) { ?>
                                    <?php if ($version->product == $product) { ?>
                                       <option value="<?php out::H($version->version); ?>"
                                           <?php if ($version->version == $chosen_version['version']) echo ' SELECTED'; ?>
                                       ><?php out::H($version->version); ?></option>
                                   <?php } ?>
                               <?php } ?>
                            </select>    
                        </span></li>
                    
                    </ul>
                </div>

    	        <div class="choices">
    		        <div class="label">Report:</div>
                    <ul>
                        <li><a <?php if (isset($nav_selection) && $nav_selection == 'overview') echo 'class="selected"'; ?> 
                            href="<?= url::base() ?>products/<?= $chosen_version['product'] ?>">Overview</a></li>
                        <li><a <?php if (isset($nav_selection) && $nav_selection == 'crashes_user') echo 'class="selected"'; ?> 
                            href="<?= url::base() ?>daily?p=<?= $chosen_version['product'] ?>&v[]=<?= $chosen_version['version'] ?>">Crashes/User</a></li>
                        <li><a <?php if (isset($nav_selection) && $nav_selection == 'top_crashes') echo 'class="selected"'; ?> 
                             href="<?= url::base() ?>topcrasher/byversion/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>">Top Crashes</a></li>
                        <li><span class="more">
                             <select id="report" name="report">
                                 <option>More Reports</option>
                        		 <option <?php if (isset($nav_selection) && $nav_selection == 'crashes_user') echo 'selected'; ?> 
                        		    value="<?= url::base() ?>daily?p=<?= $chosen_version['product'] ?>&v[]=<?= $chosen_version['version'] ?>">Crashes per User</option>
                        		 <option <?php if (isset($nav_selection) && $nav_selection == 'top_crashes') echo 'selected'; ?> 
                        		    value="<?= url::base() ?>topcrasher/byversion/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>">Top Crashes By Signature</option>
                                 <option <?php if (isset($nav_selection) && $nav_selection == 'top_url') echo 'selected'; ?> 
                                    value="<?= url::base() ?>topcrasher/byurl/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>">Top Crashes By URL</option>
                        		 <option <?php if (isset($nav_selection) && $nav_selection == 'top_domain') echo 'selected'; ?> 
                        		    value="<?= url::base() ?>topcrasher/bydomain/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>">Top Crashes By Domain</option>
                                 <option <?php if (isset($nav_selection) && $nav_selection == 'top_topsite') echo 'selected'; ?> 
                                    value="<?= url::base() ?>topcrasher/bytopsite/<?= $chosen_version['product'] ?>/<?= $chosen_version['version'] ?>">Top Crashes By Topsite</option>  
                            </select>
                        </span></li>
                    </ul>
    	        </div>
            <?php } ?>
    <?php } ?>

    </div>
    <?php } ?>

      
    <div id="mainbody">
      	<?php echo client::messageFetchHtml(); // Status and Error messages for user ?>
    	<?php echo $content; ?>
    </div>
    
    
    <div class="page-footer">
    	<div class="nav">
    		<div class="about">
    			<strong>Mozilla Crash Reports</strong>
    			-
    			Powered by Socorro
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
