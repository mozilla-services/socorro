<?php /* 
Using this widget requires
$widgetData - a list of MTBF data (see dashboard_crash_widget.php)
$j - our current index into $widgetData
$widgetData[$j] - an array with the following
  'crashes' - TODO the data for the featured MTBF report
  'other-versions' - A list of the other MTBF not featured
*/ 

$product = $widgetData[$j]['product'];
$release = $widgetData[$j]['release'];
?>
<div>
<div id="<?php echo $product . $release . "sparklines" ?>" class="meat">

<?php  
    foreach($widgetData[$j]['crashes'] as $f => $featuredMtbf){  ?>
        <div class="each-sparkline">
<?php
          $sparkData = array();
          foreach ($featuredMtbf['data'] as $i => $datum) {
    
              $sparkData[$i] = is_numeric($datum[1]) ? $datum[1] : 0;
          }
?>

    <?php echo $featuredMtbf['label'] ?> <span id="mtbf-spark-<?php echo $product . '-' . $f ?>">Loading</span>
  <script type="text/javascript">
								 $(document).ready(function(){
			   $('#<?php echo $product . $release . "sparklines"?>').click(function(){
			       window.location = "<?php echo url::base() . "mtbf/of/$product/$release" ?>";
			     })
			     .css('cursor', 'pointer');
});
$('#mtbf-spark-<?php echo $product . '-' . $f ?>').sparkline([<?php echo implode(", ", $sparkData) ?>], 
    { chartRangeMax: <?php echo $mtbfChartRangeMax ?>,
	height: "20px", width: "90px", lineColor: "#666", fillColor: "#C3C3C3"});
  </script>

        </div> <!-- each-sparkline -->
<?php
    }  //foreach
?>
</div><!-- meat -->





           <div class="expandable-menu">
               <h4 class="show-all-topcrashers"><span class="icon">[+]</span>
                    All <span class="product"><?php echo $product ?></span> Reports</h4>
               <ul class="widgetData-<?php echo $product ?>-full-list topcrash-links" style="display:  none">
<?php   foreach($widgetData[$j]['other-versions'] as $v => $version){ ?>
      <li><a href='<?php echo url::base() . "mtbf/of/" . $product . "/" . $version; ?>'>Full Report for <?php echo $version; ?></a></li>
<?php   } ?>      
               </ul>

           </div> <!-- /expandable-menu -->
</div>