
<div class="page-heading">
	<h2><?php out::H($product); ?>
        <?php if (isset($version) && !empty($version)) { ?>
            <?php out::H($version); ?>
        <?php } ?>
        Crash Data</h2>
 	<ul class="options">
        	<li><a href="<?php out::H($url_base); ?>?duration=3" <?php if ($duration == 3) echo ' class="selected"'; ?>>3 days</a></li>
        	<li><a href="<?php out::H($url_base); ?>?duration=7" <?php if ($duration == 7) echo ' class="selected"'; ?>>7 days</a></li>
        	<li><a href="<?php out::H($url_base); ?>?duration=14" <?php if ($duration == 14) echo ' class="selected"'; ?>>14 days</a></li>
        </ul>
</div>


<div class="panel">
    <div class="title">
        <h2>Crashes per 100  Active Daily Users</h2>
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
        <h2>Crash Reports</h2>
    </div>

    <div class="body">
        <div id="release_channels">
    <?php
	$i = 0;
	
	 // sort top crashers from highest to lowest
	function compare($prod1, $prod2) {

		$firstProdVersion = $prod1->version;
		$secondProdVersion = $prod2->version;

		// get only the number from the string avoiding decimals and string characters
		$firstVerNumber = (int) substr($firstProdVersion, 0, strrpos($firstProdVersion, "."));
		$secondVerNumber = (int) substr($secondProdVersion, 0, strrpos($secondProdVersion, "."));

		if($firstVerNumber == $secondVerNumber) {
			return 0;
		}
		return $secondVerNumber - $firstVerNumber;
	}

	usort($top_crashers, "compare");
	
        foreach ($top_crashers as $prodversion) {
            $num_columns = count($top_crashers);
            $i++;
    ?>
        <div class="release_channel <?php if ($i < $num_columns) echo ' border_right'; ?>">
            <h4><?=$prodversion->product?> <?=$prodversion->version?></h4>
            <ul>
              <li class="emphatic"><a href="<?php echo url::base() . "topcrasher/byversion/" . $prodversion->product . "/" . $prodversion->version . "/" . $duration; ?>">Top Crashers</a></li>
              <li class="emphatic"><a href="<?php echo url::base() . "products/" . $prodversion->product . "/versions/" . $prodversion->version . "/topchangers" . "?duration=" . $duration; ?>">Top Changers</a></li>
              <li><a href="<?php echo url::base() . "topcrasher/byversion/" . $prodversion->product . "/" . $prodversion->version . "/" . $duration . "/plugin"; ?>">Top Plugin Crashers</a></li>
              <li><a href="<?php echo url::base() . "topcrasher/byurl/" . $prodversion->product . "/" . $prodversion->version; ?>">Top Crashes by URL</a></li>
              <li><a href="<?php echo url::base() . "topcrasher/bydomain/" . $prodversion->product . "/" . $prodversion->version; ?>">Top Crashes by Domain</a></li>
              <li><a href="<?php echo url::base() . "topcrasher/bytopsite/" . $prodversion->product . "/" . $prodversion->version; ?>">Top Crashes by Topsite</a></li>
            </ul>
        </div>
    <?php } ?>
        </div>
    <br class="clear" />
    </div>
</div>
<br class="clear" />
