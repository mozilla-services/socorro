<?php slot::start('head') ?>
    <title>Top Crashers for <?php out::H($product) ?> <?php out::H($version) ?> </title>
    <?php echo html::script(array(
      	'js/jquery/plugins/ui/jquery.tablesorter.min.js',
        'js/socorro/topcrashbyurl.js'
    ))?>
    <?php echo html::stylesheet(array(
        'css/flora/flora.tablesorter.css'
    ), 'screen')?>
    <script type="text/javascript">
        $(document).ready(function() { 
              $('#topsitelist').tablesorter(); 
        } ); 
    </script>
<?php slot::end() ?>


<h1 class="first">Top Crashers By Top Site Ranking for <span id="tcburl-product"><?php out::H($product) ?></span> <span id="tcburl-version"><?php out::H($version)?></span></h1>

<p>Below are the top crash signatures by Top Site Ranking from <?php echo $beginning ?> to <?php echo $ending_on ?></p>

<p>
	Top Crashers:
	<a class="trend-nav" href="../../bydomain/<?php echo $product ?>/<?php echo $version ?>">Breakdown by Domain</a>,
	<a class="trend-nav" href="../../byurl/<?php echo $product ?>/<?php echo $version ?>">Breakdown by URL</a>
</p>

<table id="topsitelist" class="tablesorter">
  <thead>
  	<tr>
		<th>Top 1000 Site</th>
		<th>Domain</th>
		<th>&#35;</th>
	</tr>
  </thead>
  <tbody>
    <?php $row = 0 ?>
    <?php foreach($top_crashers as $crash){ ?>
      <tr class="<?php echo ( ($row) % 2) == 0 ? 'even' : 'odd' ?>">
      		<td width="100"><?php if (isset($crash->rank)) out::H($crash->rank); ?></td>
        	<td><span class="url"><?php out::H($crash->domain) ?></td>
        	<td class="domain-crash-count"><?php out::H($crash->count)?></td>
      </tr>
    <?php $row += 1; ?>
    <?php } ?>
  </tbody>
</table>


