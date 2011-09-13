<?php slot::start('head') ?>
    <title>Top Crashers for  <?php out::H($product) ?> <?php out::H($version) ?> </title>
    <?php echo html::script(array(
        'js/socorro/topcrashbyurl.js'
    ))?>
    <?php echo html::stylesheet(array(
        'css/flora/flora.tablesorter.css'
    ), 'screen')?>
<?php slot::end() ?>


<div class="page-heading">
	<h2>Top Crashers By Domain for <span id="tcburl-product"><?php out::H($product) ?></span> <span id="tcburl-version"><?php out::H($version)?></span></h2>
    <ul class="options">
        <li><a href="<?php echo url::base(); ?>topcrasher/byversion/<?php echo $product ?>/<?php echo $version ?>">By Signature</a></li>
        <li><a href="<?php echo url::base(); ?>topcrasher/byurl/<?php echo $product ?>/<?php echo $version ?>">By URL</a></li>
        <li><a href="<?php echo url::base(); ?>topcrasher/bydomain/<?php echo $product ?>/<?php echo $version ?>" class="selected">By Domain</a></li>
        <li><a href="<?php echo url::base(); ?>topcrasher/bytopsite/<?php echo $product ?>/<?php echo $version ?>">By Topsite</a></li>
    </ul>
</div>


<div class="panel">
    <div class="body notitle">
        <p>Below are the top crash signatures by Domain from <?php echo $beginning ?> to <?php echo $ending_on ?></p>

<?php
    // Bug# 470525 - no link to domain
?>
<table id="tc_by_domain" class="tablesorter">
  <thead>
  	<tr>
		<th>Domain</th>
		<th>&#35;</th>
		<th>Top 1000 Site</th>
	</tr>
  </thead>
  <tbody>
    <?php $row = 0 ?>
    <?php foreach($top_crashers as $crash){ ?>

      <tr class="<?php echo ( ($row) % 2) == 0 ? 'even' : 'odd' ?>">
            <td>
            <?php if (!strstr($crash->domain, '_BLOCKED')) { ?>
        	<div id="domain-to-url<?php echo $row; ?>" class="tcburl-toggler tcburl-domainToggler">+</div><a id="tcburl-url<?php echo $row ?>" class="tcburl-domainToggler" href="#"><span class="label tcburl-domainToggler">Expand</span> <span class="url tcburl-domainToggler"><?php out::H($crash->domain) ?></span></a>
            <?php } else { ?>
            <?php out::H($crash->domain); ?>
            <?php } ?>
            </td>

        	<td class="domain-crash-count"><?php out::H($crash->count)?></td>
        	<td><?php if (isset($crash->rank)) out::H($crash->rank); ?></td>
      </tr>
      <tr id="tcburl-domainToggle-row<?php echo $row; ?>" style="display: none"><td colspan="2"><?php
					    echo html::image( array('src' => 'img/loading.png', 'width' => '16', 'height' => '17',
								    'alt' => 'More Content Loading')); ?></td></tr>
    <?php $row += 1;
          } ?>
  </tbody>
</table>

    </div>
</div>

  <script type="text/javascript">//<![CDATA[
  var SocTCByURL = {};
  SocTCByURL.urls = <?php echo json_encode( $top_crashers ); ?>;
  SocTCByURL.domains = [
		      {domain: 'www.myspace.com', count: 1200,
		       urls: [SocTCByURL.urls[1], SocTCByURL.urls[2]]},
		      {domain: 'www.youtube.com', count: 300, urls:
		      [SocTCByURL.urls[0]]}
			];
//]]></script>
