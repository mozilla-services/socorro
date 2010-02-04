
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


<div class="panel product_dashboard_left">

	<div class="title">
		<h2>Top Changers</h2>
		<div class="choices">
        	<ul>
                <li><a href="#" id="click_up" class="selected">Up</a></li>
                <li><a href="#" id="click_down">Down</a></li>
        	</ul>
        </div>
    </div>

    <div class="body">
        
        <?php foreach ($top_changers as $key => $changers) { ?>
            <table id="top_changers_<?= $key; ?>" <?php if ($key != 'up') echo 'class="hidden"'; ?> >
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
        <?php } ?>
        <br class="clear_both">

    </div>
    
</div>


<div class="panel product_dashboard_right">
	<div class="title">
		<h2>Crashes per 1k ADU</h2>
    </div>

<?php if (!empty($graph_data)) { ?>

        <div class="body">
	        <div id="daily_crash_graph">
				<div id="sig-history-graph"></div>
	        </div>

            <br class="clear" />
	    </div>
	
<?php } else { ?>
	
	<div class="body">
		<p>No Active Daily User crash data is available for this report.</p>
	</div>
	
<?php } ?>
</div>

<br class="clear" />
<br class="clear" />

<div class="panel">
	<div class="title">
		<h2><?php out::H($product); ?> 
            <?php if (isset($version) && !empty($version)) { ?>
                <?php out::H($version); ?>
            <?php } ?>
            Top Crashers</h2>

        <?php /* @todo Re-implement when we can refresh using ajax
        <div class="choices">
        	<ul>
                <li><a href="<?= $url_top_crashers; ?>" class="selected">Top Crashers</a></li>
                <li><a href="<?= $url_top_domains; ?>">Top Domains</a></li>
                <li><a href="<?= $url_top_topsites; ?>">Top Topsites</a></li>              
                <li><a href="<?= $url_top_urls; ?>">Top URLs</a><li>
        	</ul>
        </div>
        */ ?>

    </div>
    
    <div class="body">
    <?php
        $i = 0;
        foreach ($top_crashers as $prodversion){ 
            $num_columns = count($top_crashers);
            $url = url::base() . "topcrasher/byversion/{$prodversion['product']}/{$prodversion['version']}";
            $i++;
    ?>

        <div class="product_topcrasher<?php if ($i < $num_columns) echo ' border_right'; ?>">
            <h4><?=$prodversion['product']?> <?=$prodversion['version']?> <span class="view_all"><a href="<?php out::H($url)?>">View all</a></span></h4>
            <?php 
                foreach ($prodversion['crashers'] as $crasher) {
                    $sigParams = array(
                      'range_value' => '2',
                      'range_unit'  => 'weeks',
                      'signature'   => $crasher->signature
                    );
                    if (property_exists($crasher, 'version')) {
                      $sigParams['version'] = $crasher->product . ':' . $crasher->version;
                    } else {
                      $sigParams['branch'] = $crasher->branch;
                    }
                    $link_url =  url::base() . 'report/list?' . html::query_string($sigParams);
                    
                    if (empty($crasher->signature)) {
                      $sig = '(no signature)';
                    } else {
                      $sig = $crasher->signature;
                    }
                ?>
                <div class="crash">
                    <p><a href="<?php out::H($link_url)?>" title="<?php out::H($sig)?>"><?php out::H($sig)?></a></p>
                    <span><?php out::H($crasher->total)?></span>
                </div>
            <?php } ?>
        </div>
    <?php } ?>

    <br class="clear" />

    </div>

</div>

<br class="clear" />


