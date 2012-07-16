<?php
    $url_params = array($product, $version);
    if(isset($duration)) {
        array_push($url_params, $duration);
    }
    if (isset($crash_type)) {
        array_push($url_params, $crash_type);
    }
    $url_params = implode("/", $url_params);
?>
<ul class="options">
    <li><a href="<?php echo url::base(); ?>topcrasher/byversion/<?php echo $url_params ?>"
        <?php if(isset($date_range_type) && ($date_range_type != 'build')) { ?> class="selected" <?php } ?>>By Crash Date</a>
    </li>
    <li><a href="<?php echo url::base(); ?>topcrasher/by_build_date/<?php echo $url_params ?>"
        <?php if(isset($date_range_type) && ($date_range_type == 'build')) { ?> class="selected" <?php } ?>>By Build Date</a>
    </li>
</ul>