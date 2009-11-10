<?php slot::start('head') ?>
    <title>Top Crashers for  <?php out::H($product) ?> <?php out::H($version) ?> </title>
    <?php echo html::script(array(

        'js/socorro/topcrashbyurl.js',
    ))?>
    <?php echo html::stylesheet(array(
        'css/flora/flora.tablesorter.css'
    ), 'screen')?>
<?php slot::end() ?>

    <h1 class="first">Top Crashers By URL for <span id="tcburl-product"><?php out::H($product) ?></span> <span id="tcburl-version"><?php out::H($version)?></span> </h1>
<div>Below are the top crash signatures by URL from <?php echo $beginning ?> to <?php echo $ending_on ?></div>
<a class="trend-nav" href="../../bydomain/<?php echo $product ?>/<?php echo $version ?>">Switch to by breakdown by Domain</a>
<table class="tablesorter">
  <thead>
  <tr><th>URL</th><th>&#35;</th></tr>
  </thead>
  <tbody>
    <?php $row = 0 ?>
    <?php foreach($top_crashers as $crash){ ?>
      
      <tr class="<?php echo ( ($row) % 2) == 0 ? 'even' : 'odd' ?>">
        <td><div id="url-to-sig<?php echo $row; ?>" class="tcburl-toggler tcburl-urlToggler">+</div> <a id="tcburl-url<?php echo $row ?>" class="tcburl-urlToggler" href="#">Expand <span class="url"><?php out::H($crash->url) ?></span></a> <a  href="<?php out::H($crash->url) ?>">Open This URL</a> </td>
        <td class="url-crash-count"><?php out::H($crash->count)?></td>
      </tr>
      <tr id="tcburl-urlToggle-row<?php echo $row; ?>" style="display: none"><td colspan="2"><?php 
					    echo html::image( array('src' => 'img/loading.png', 'width' => '16', 'height' => '17', 
								    'alt' => 'More Content Loading')); ?></td></tr>
    <?php $row += 1;
          } ?>
  </tbody>
</table>
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