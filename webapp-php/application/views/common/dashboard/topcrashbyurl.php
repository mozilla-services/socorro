<div>
<?php     if ( count($widgetData[$j]['crashes']) > 0) {  ?>
<dl>
<?php
                for($i =0; $i < count($widgetData[$j]['crashes']); $i++){
                    $topcrash = $widgetData[$j]['crashes'][$i];
                    $url = strtr($topcrash->url,
				 array("http://" => "",
				       "https://" => "",
				       "www." => ""));
?>
	        <dt title="<?php echo $topcrash->url ?>"><?php echo ($i + 1); ?> <?php echo out::H($url); ?></dt>
                <dd title="Crash Count"><?php echo $topcrash->count; ?></dd>
<?php
                } //for($i =0; $i < ...
?>
            </dl>


<?php
    } //if ( count($widgetData[$j]['crashes']) > 0) { 

    $product = $widgetData[$j]['name'];
?>
<a class="full-report" title="View the full <?php echo $widgetData[$j]['name'] ?> <?php echo $widgetData[$j]['version'] ?> report"
     href="<?php echo url::base() ?>/topcrasher/byurl/<?php echo $widgetData[$j]['name'] ?>/<?php echo $widgetData[$j]['version'] ?>">Full Report</a>

           <div class="expandable-menu">
               <h4 class="show-all-topcrashers"><span class="icon">[+]</span>
                    All <span class="product"><?php echo $product ?></span> Reports</h4>

               <ul class="widgetData-<?php echo $product ?>-full-list topcrash-links" style="display:  none">
<?php   
foreach($widgetData[$j]['other-versions'] as $v => $version){ ?>
      <li><a href='<?php echo url::base() . "topcrasher/byurl/" . $product . "/" . $version; ?>'>Full Report for <?php echo $version; ?></a></li>
<?php   } ?>      
               </ul>
           </div> <!-- /expandable-menu -->
</div>