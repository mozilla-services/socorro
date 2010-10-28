
<div class="page-heading">
	<h2><?php out::H($product); ?> 
        <?php if (isset($version) && !empty($version)) { ?>
            <?php out::H($version); ?>
        <?php } ?>
        Crash Data</h2>
        
    <ul class="options">
        <li><a href="<?php out::H($url_base); ?>?duration=7" <?php if ($duration == 7) echo ' class="selected"'; ?>>7 days</a></li>
        <li><a href="<?php out::H($url_base); ?>?duration=14" <?php if ($duration == 14) echo ' class="selected"'; ?>>14 days</a></li>
        <li><a href="<?php out::H($url_base); ?>?duration=28" <?php if ($duration == 28) echo ' class="selected"'; ?>>28 days</a></li>
	</ul>
</div>


<div class="panel">
	<div class="title">
		<h2>Crashes per Active Daily User</h2>
    </div>

	<div class="body">
        <?php if (!empty($graph_data)) { ?>
		    <div id="adu-chart"></div>
        <?php } else { ?>
            <p>No Active Daily User crash data is available for this report.</p>
        <?php } ?>
	</div>
	
</div>


<div class="panel">
	<div class="title">
		<h2><?php out::H($product); ?> 
            <?php if (isset($version) && !empty($version)) { ?>
                <?php out::H($version); ?>
            <?php } ?>
            Top Crashers</h2>

        <div class="choices">
        	<ul>
                <li><a id="click_top_crashers" href="#" class="selected">Top Crashers</a></li>
                <li><a id="click_top_changers" href="#">Top Changers</a></li>
        	</ul>
        </div>

    </div>
    
    <div class="body">
        <div id="top_crashers">
    <?php
        $i = 0;
        foreach ($top_crashers as $prodversion){ 
            $num_columns = count($top_crashers);
            $url = url::base() . "topcrasher/byversion/" . $prodversion->product . "/" . $prodversion->version;
            $i++;
    ?>
 

        <div class="product_topcrasher<?php if ($i < $num_columns) echo ' border_right'; ?>">
            <h4><?=$prodversion->product?> <?=$prodversion->version?> <span class="view_all"><a href="<?php out::H($url)?>">View all</a></span></h4>
            <?php 
                $tc_count = 1;
                if (isset($prodversion->crashes) && !empty($prodversion->crashes)) {
                    foreach ($prodversion->crashes as $crasher) {
                        if ($tc_count <= $top_crashers_limit) { 
                            $tc_count++;
                        
                            $sigParams = array(
                              'range_value' => '2',
                              'range_unit'  => 'weeks',
                              'signature'   => $crasher->signature,
                              'version' => $prodversion->product . ':' . $prodversion->version
                            );
                            $link_url =  url::base() . 'report/list?' . html::query_string($sigParams);
                            
                            if (empty($crasher->signature)) {
                              $sig = '(no signature)';
                            } else {
                              $sig = $crasher->signature;
                            }
                        ?>
                        <div class="crash">
                            <p><a href="<?php out::H($link_url)?>" title="<?php out::H($sig)?>"><?php out::H($sig)?></a></p>
                            <span><?php out::H(number_format($crasher->count)); ?></span>
                        </div>
                    <?php 
                        }
                    } 
                }
            ?>
        </div>
    <?php } ?>

    </div>

    <div id="top_changers" class="hidden">

    <?php if (isset($top_changers) && !empty($top_changers)) { ?>
        <?php foreach ($top_changers as $key => $changers) { ?>
            <div class="product_topchanger<?php if ($key == 'up') echo ' border_right'; ?>">            
                <table id="top_changers_<?= $key; ?>" class="top_changers">
                    <tr>
                        <th>Change</th>
                        <th>&nbsp; Signature</th>
                    </tr>
                    <?php 
                        foreach ($changers as $changer) { 
                            $range_value = 1;
                            if ($duration == 14) {
                                $range_value = 2;
                            } elseif ($duration == 28) {
                                $range_value = 4;
                            }
                
                            $sigParams = array(
                                'range_value' => $range_value,
                                'range_unit'  => 'weeks',
                                'signature' => $changer['signature'],
                                'version' => $product
                	        );
                        
                            if (!empty($version)) {
                                $sigParams['version'] .= ":" . $version;
                            }
                
                	        if (is_null($changer['signature'])) {
                			    $display_signature = Crash::$null_sig;
                		    } else if(empty($changer['signature'])) {
                			    $display_signature = Crash::$empty_sig;
                		    } else {
                			    $display_signature = $changer['signature'];
                		    }
                		    
                            $link_url =  url::base() . 'report/list?' . html::query_string($sigParams);
                        ?>
                
                        <tr>
                            <td><div class="trend <?= $changer['trendClass'] ?>"><?= $changer['changeInRank']; ?></div></td>        
                            <td><a class="signature" href="<?php out::H($link_url) ?>" 
                               title="View reports with this crasher."><?php out::H($display_signature); ?></a>
                            </td> 
                        </tr>
                    <?php } ?>
                </table>
            </div>
        <?php } ?>
    <?php } else { ?>
        <p>Top changers currently unavailable.</p>
    <?php } ?>
    </div>


    <br class="clear" />
    </div>

</div>

<br class="clear" />


