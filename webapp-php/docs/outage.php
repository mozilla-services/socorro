<?php 
$outage_message = "We are <a href='http://blog.mozilla.com/webdev/2009/01/20/socorro-database-partitioning-is-coming/'>repartitioning the database</a>. We expect this to take at most 48 hours. Thanks for your patience.";
?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">

<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en-US" lang="en-US" dir="ltr">

<head>
	<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
	<title>Crash Reporter Service Outage</title>
	<script type="text/javascript" src="http://status.mozilla.com/js/util.js"></script>
	<link rel="stylesheet" type="text/css" href="http://status.mozilla.com/includes/yui/2.5.1/reset-fonts-grids/reset-fonts-grids.css" />
	<link rel="stylesheet" type="text/css" href="http://status.mozilla.com/includes/yui/2.5.1/menu/assets/skins/sam/menu.css" />

	<link rel="stylesheet" type="text/css" href="http://status.mozilla.com/style/tignish/template.css" media="screen" />
	<link rel="stylesheet" type="text/css" href="http://status.mozilla.com/style/tignish/content.css" media="screen" />
	<script type="text/javascript" src="http://status.mozilla.com/includes/yui/2.5.1/yahoo-dom-event/yahoo-dom-event.js"></script>
	<script type="text/javascript" src="http://status.mozilla.com/includes/yui/2.5.1/container/container_core-min.js"></script>
	<script type="text/javascript" src="http://status.mozilla.com/includes/yui/2.5.1/menu/menu-min.js"></script>
	<script type="text/javascript" src="http://status.mozilla.com/js/mozilla-menu.js"></script>
    
    <link rel="stylesheet" type="text/css" href="http://status.mozilla.com/style/tignish/outages-page.css" media="screen" />

</head>

<body id="outages" class="">

<!-- SiteCatalyst Reporting -->
<script type="text/javascript">s_account="mozillacom";</script>
<script src="http://status.mozilla.com/js/s_code.js" type="text/javascript"></script>
<script type="text/javascript">// <![CDATA[
// add classes to body to indicate browser version and JavaScript availabiliy
if (document.body.className == '') {
	document.body.className = 'js';
} else {
	document.body.className += ' js';
}

if (gPlatform == 1) {
	document.body.className += ' platform-windows';
} else if (gPlatform == 3 || gPlatform == 4) {
	document.body.className += ' platform-mac';
} else if (gPlatform == 2) {
	document.body.className += ' platform-linux';
}

// ]]></script>

<div id="breadcrumbs">
    
</div>

<noscript><div id="no-js-feature"></div></noscript>

<div id="wrapper">
<div id="doc">

	<div id="nav-access">
		<a href="outages.html#nav-main">skip to navigation</a>
		<a href="outages.html#switch">switch language</a>
	</div>

	<!-- start #header -->
	<div id="header">
		<div>
		<h1><a href="http://www.mozilla.com/en-US/" title="Back to home page"><img src="http://status.mozilla.com/img/tignish/template/mozilla-logo.png" height="56" width="145" alt="Mozilla" /></a></h1>
		
<!-- start #nav-main -->
<div id="nav-main" class="yuimenubar yuimenubarnav">
  <div class="bd">
    <ul class="first-of-type">
<li id="menu_products" class="yuimenubaritem"><a href="http://www.mozilla.com/en-US/products/">Products</a>

      <div class="yuimenu">
        <div class="bd">
          <ul>
<li id="submenu_firefox" class="yuimenuitem"><a href="http://www.mozilla.com/en-US/products/firefox/">Firefox</a></li><li id="submenu_thunderbird" class="yuimenuitem"><a href="http://www.mozilla.com/en-US/products/thunderbird/">Thunderbird</a></li></ul>
        </div>
      </div>
      </li><li id="menu_addons" class="yuimenubaritem"><a href="https://addons.mozilla.org/">Add-ons</a>
      <div class="yuimenu">

        <div class="bd">
          <ul>
<li id="submenu_addons_all" class="yuimenuitem"><a href="https://addons.mozilla.org/firefox/">All Add-ons</a></li><li id="submenu_addons_recommended" class="yuimenuitem"><a href="https://addons.mozilla.org/firefox/recommended">Recommended</a></li><li id="submenu_addons_popular" class="yuimenuitem"><a href="https://addons.mozilla.org/firefox/browse/type:1/cat:all?sort=popular">Popular</a></li><li id="submenu_addons_themes" class="yuimenuitem"><a href="https://addons.mozilla.org/firefox/browse/type:2">Themes</a></li><li id="submenu_addons_search" class="yuimenuitem"><a href="https://addons.mozilla.org/firefox/browse/type:4">Search Engines</a></li><li id="submenu_addons_plugins" class="yuimenuitem"><a href="https://addons.mozilla.org/firefox/browse/type:7">Plugins</a></li></ul>
        </div>
      </div>
      </li><li id="menu_support" class="yuimenubaritem"><a href="http://support.mozilla.com/">Support</a>

      <div class="yuimenu">
        <div class="bd">
          <ul>
<li id="submenu_support_kb" class="yuimenuitem"><a href="http://support.mozilla.com/en-US/kb/">Firefox Knowledge Base</a></li><li id="submenu_support_forum" class="yuimenuitem"><a href="http://support.mozilla.com/en-US/forum/">Firefox Support Forum</a></li><li id="submenu_support_other" class="yuimenuitem"><a href=" http://support.mozilla.com/en-US/kb/Other+Firefox+support">Other Firefox Support</a></li><li id="submenu_support_thunderbird" class="yuimenuitem"><a href="http://www.mozilla.org/support/thunderbird/">Thunderbird Support</a></li></ul>
        </div>
      </div>
      </li><li id="menu_community" class="yuimenubaritem"><a href="http://www.mozilla.com/en-US/manyfaces/">Community</a>

      <div class="yuimenu">
        <div class="bd">
          <ul>
<li id="submenu_community_addons" class="yuimenuitem"><a href="http://addons.mozilla.org/">Add-ons</a></li><li id="submenu_community_bugzilla" class="yuimenuitem"><a href="https://bugzilla.mozilla.org/">Bugzilla</a></li><li id="submenu_community_devmo" class="yuimenuitem"><a href="http://developer.mozilla.org/">Mozilla Developer Center</a></li><li id="submenu_community_labs" class="yuimenuitem"><a href="http://labs.mozilla.com/">Mozilla Labs</a></li><li id="submenu_community_mozillaorg" class="yuimenuitem"><a href="http://www.mozilla.org/">Mozilla.org</a></li><li id="submenu_community_mozillazine" class="yuimenuitem"><a href="http://www.mozillazine.org/">MozillaZine</a></li><li id="submenu_community_planet" class="yuimenuitem"><a href="http://planet.mozilla.org/">Planet Mozilla</a></li><li id="submenu_community_qmo" class="yuimenuitem"><a href="http://quality.mozilla.org/">QMO</a></li><li id="submenu_community_spreadfirefox" class="yuimenuitem"><a href="http://www.spreadfirefox.com/">SpreadFirefox</a></li><li id="submenu_community_support" class="yuimenuitem"><a href="http://support.mozilla.com/">Support</a></li></ul>

        </div>
      </div>
      </li><li id="menu_aboutus" class="yuimenubaritem"><a href="http://www.mozilla.com/en-US/about/">About</a>
      <div class="yuimenu">
        <div class="bd">
          <ul>
<li id="submenu_about" class="yuimenuitem"><a href="http://www.mozilla.com/en-US/about/whatismozilla.html">What is Mozilla?</a></li><li id="submenu_getinvolved" class="yuimenuitem"><a href="http://www.mozilla.com/en-US/about/get-involved.html">Get Involved</a></li><li id="submenu_press" class="yuimenuitem"><a href="http://www.mozilla.com/en-US/press/">Press Center</a></li><li id="submenu_careers" class="yuimenuitem"><a href="http://www.mozilla.com/en-US/about/careers.html">Careers</a></li><li id="submenu_partnerships" class="yuimenuitem"><a href="http://www.mozilla.com/en-US/about/partnerships.html">Partnerships</a></li><li id="submenu_licensing" class="yuimenuitem"><a href="http://www.mozilla.org/foundation/licensing.html">Licensing</a></li><li id="submenu_blog" class="yuimenuitem"><a href="http://blog.mozilla.com/">Blog</a></li><li id="submenu_store" class="yuimenuitem"><a href="http://store.mozilla.org/">Store</a></li><li id="submenu_contact" class="yuimenuitem"><a href="http://www.mozilla.com/en-US/about/contact.html">Contact Us</a></li></ul>

        </div>
      </div>
      </li></ul>
  </div>
</div>
<!-- end #nav-main -->

		<form id="moz_global_search" action="http://www.mozilla.com/en-US/search/" method="get"><div>
			<input type="hidden" name="hits_per_page" id="hits_per_page" value="" />
			<input type="hidden" name="hits_per_site" id="hits_per_site" value="" />

			<input type="text" name="query" id="query" value="" /><input type="image" src="http://status.mozilla.com/img/tignish/content/search-button.png" id="submit" value="Search" />
		</div></form>
		</div>
	</div>
	<!-- end #header -->

	<hr class="hide" />
<div id="main-feature">
	<h2>Repairs in Progress</h2>

	<p>The Crash Reporter is unavailable at the moment. We’ll be back up and running again before long, so please try again soon. Thanks for your patience!</p>
<?php if(isset($outage_message)){ ?>
        <h3>Details</h3>
        <p><?php echo $outage_message; ?> </p>
<?php   } ?>
</div>


		

<div id="footer-divider"><hr /></div>

</div><!-- end #doc -->
</div><!-- end #wrapper -->

	<!-- start #footer -->
	<div id="footer">
	<div id="footer-contents">

		<form id="lang_form" dir="ltr" method="get" action="outages.html"><div>
			<label for="flang">Other languages:</label>
			
<select id="flang" name="flang" dir="ltr" onchange="this.form.submit()">    <option value="ca" >Catal&#224;</option>
    <option value="cs" >&#268;e&#353;tina</option>
    <option value="da" >Dansk</option>

    <option value="de" >Deutsch</option>
    <option value="el" >&#917;&#955;&#955;&#951;&#957;&#953;&#954;&#940;</option>
    <option value="es" >Espa&#241;ol</option>
    <option value="eu" >Euskara</option>
    <option value="en-GB" >English (British)</option>
    <option value="en-US" selected="selected">English (US)</option>

    <option value="fr" >Fran&#231;ais</option>
    <option value="he" >&#1506;&#1489;&#1512;&#1497;&#1514;</option>
    <option value="it" >Italiano</option>
    <option value="lt" >Lietuvi&#371;</option>
    <option value="hu" >Magyar</option>
    <option value="nl" >Nederlands</option>

    <option value="no" >Norsk bokm&#229;l</option>
    <option value="pl" >Polski</option>
    <option value="pt-BR" >Portugu&#234;s (do Brasil)</option>
    <option value="pt-PT" >Portugu&#234;s (Europeu)</option>
    <option value="ro" >Rom&#226;n&#259;</option>

    <option value="ru" >&#1056;&#1091;&#1089;&#1089;&#1082;&#1080;&#1081;</option>
    <option value="sk" >Slovensk&#253;</option>
    <option value="sq" >Shqip</option>
    <option value="fi" >Suomi</option>
    <option value="tr" >T&#252;rk&#231;e</option>
    <option value="zh-CN" >&#20013;&#25991; (&#31616;&#20307;)</option>

    <option value="ja" >&#26085;&#26412;&#35486;</option>
    <option value="ko" >&#54620;&#44397;&#50612;</option>
    <option value="uk" >&#1059;&#1082;&#1088;&#1072;&#1111;&#1085;&#1089;&#1100;&#1082;&#1072;</option>
    <option value="zh-TW" >&#27491;&#39636;&#20013;&#25991; (&#32321;&#39636;)</option>
</select>

			<noscript>
				<div><input type="submit" id="lang_submit" value="Go" /></div>
			</noscript>
		</div></form>

		<ul id="footer-menu">
			<li><a href="http://www.mozilla.com/en-US/firefox/">Firefox</a>
				<ul>
					<li><a href="http://www.mozilla.com/en-US/firefox/features/">Features</a></li>
					<li><a href="http://www.mozilla.com/en-US/firefox/security/">Security</a></li>
					<li><a href="http://www.mozilla.com/en-US/firefox/customize/">Customization</a></li>

					<li><a href="http://www.mozilla.com/en-US/firefox/organic/">100% Organic Software</a></li>
					<li><a href="http://www.mozilla.com/en-US/firefox/tips/">Tips and Tricks</a></li>
					<li><a href="http://www.mozilla.com/en-US/firefox/3.0.1/releasenotes/">Release Notes</a></li>
					<li><a href="http://www.mozilla.com/en-US/firefox/all.html">Other Systems and Languages</a></li>
				</ul>
			</li>
			<li><a href="https://addons.mozilla.org/" class="external">Add-ons</a>

				<ul>
					<li><a href="https://addons.mozilla.org/firefox/" class="external">All Add-ons</a></li>
					<li><a href="https://addons.mozilla.org/firefox/recommended" class="external">Recommended</a></li>
					<li><a href="https://addons.mozilla.org/firefox/browse/type:1/cat:all?sort=popular" class="external">Popular</a></li>
					<li><a href="https://addons.mozilla.org/firefox/browse/type:2" class="external">Themes</a></li>
					<li><a href="https://addons.mozilla.org/firefox/browse/type:4" class="external">Search Engines</a></li>

					<li><a href="https://addons.mozilla.org/firefox/browse/type:7" class="external">Plugins</a></li>
				</ul>
			</li>
			<li><a href="http://support.mozilla.com/">Support</a>
				<ul>
					<li><a href="http://support.mozilla.com/en-US/kb/">Firefox Knowledge Base</a></li>
					<li><a href="http://support.mozilla.com/en-US/forum/">Firefox Support Forum</a></li>

					<li><a href="http://support.mozilla.com/en-US/kb/Other+Firefox+support">Other Firefox Support</a></li>
					<li><a href="http://www.mozilla.org/support/thunderbird/" class="external">Thunderbird Support</a></li>
				</ul>
			</li>
			<li><a href="http://www.mozilla.com/en-US/manyfaces/">Community</a>
				<ul>
					<li><a href="https://addons.mozilla.org/" class="external">Add-ons</a></li>

					<li><a href="https://bugzilla.mozilla.org/" class="external">Bugzilla</a></li>
					<li><a href="http://developer.mozilla.org/" class="external">Mozilla Developer Center</a></li>
					<li><a href="http://labs.mozilla.com/" class="external">Mozilla Labs</a></li>
					<li><a href="http://www.mozilla.org/" class="external">Mozilla.org</a></li>
					<li><a href="http://www.mozillazine.org/" class="external">MozillaZine</a></li>
					<li><a href="http://planet.mozilla.org/" class="external">Planet Mozilla</a></li>

					<li><a href="http://quality.mozilla.org/" class="external">QMO</a></li>
					<li><a href="http://www.spreadfirefox.com/" class="external">SpreadFirefox</a></li>
					<li><a href="http://support.mozilla.com/">Support</a></li>
				</ul>
			</li>
			<li><a href="http://www.mozilla.com/en-US/about/">About</a>
				<ul>

					<li><a href="http://www.mozilla.com/en-US/about/whatismozilla.html">What is Mozilla?</a></li>
					<li><a href="http://www.mozilla.com/en-US/about/get-involved.html">Get Involved</a></li>
					<li><a href="http://www.mozilla.com/en-US/press/">Press Center</a></li>
					<li><a href="http://www.mozilla.com/en-US/about/careers.html">Careers</a></li>
					<li><a href="http://www.mozilla.com/en-US/about/partnerships.html">Partnerships</a></li>
					<li><a href="http://www.mozilla.org/foundation/licensing.html" class="external">Licensing</a></li>

					<li><a href="http://blog.mozilla.com/" class="external">Blog</a></li>
					<li><a href="http://store.mozilla.org/" class="external">Store</a></li>
					<li><a href="http://www.mozilla.com/en-US/about/contact.html">Contact Us</a></li>
				</ul>
			</li>
		</ul>

		<div id="copyright">

			<p><strong>Copyright &#169; 2005&#8211;2008 Mozilla.</strong> All rights reserved.</p>
			<p id="footer-links"><a href="http://www.mozilla.com/en-US/privacy-policy.html">Privacy Policy</a> &nbsp;|&nbsp; 
			<a href="http://www.mozilla.com/en-US/about/legal.html">Legal Notices</a></p>
		</div>

	</div>
	</div>
	<!-- end #footer -->
	<script type="text/javascript">// <![CDATA[
		var s_code=s.t();if(s_code)document.write(s_code);
	// ]]></script>
	<!-- end SiteCatalyst code version: H.14 -->
	<script type="text/javascript" src="http://status.mozilla.com/js/__utm.js"></script>
	<script type="text/javascript" src="http://status.mozilla.com/js/track.js"></script>

	

</body>
</html>
