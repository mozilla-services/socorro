<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<?php
    $url_params = array($product, $version);
    if(isset($os)) {
        array_push($url_params, $os);
        $os_by_build_date = "/build";
    }
    if(isset($duration)) {
        array_push($url_params, $duration);
    }
    if (isset($crash_type)) {
        array_push($url_params, $crash_type);
    }
    $url_params = implode("/", $url_params);
    // For the by crash date link, always use the following params and not the $url_prams else,
    // on the by os page the os string will be added to the params and hence appended to the
    // link. This breaks the by version page.
    $byversion_params = $product . "/" . $version . "/" . $duration . "/" . $crash_type;
?>
<ul class="options">
    <li><a href="<?php echo url::base(); ?>topcrasher/byversion/<?php echo $byversion_params ?>"
        <?php if(isset($date_range_type) && ($date_range_type != 'build')) { ?> class="selected" <?php } ?>>By Crash Date</a>
    </li>
    <?php if (isset($has_builds) && $has_builds) { ?>
    <li><a href="<?php echo url::base(); ?>topcrasher/<?php echo (isset($os_by_build_date)
                        ? "byos/" . $url_params . $os_by_build_date : "by_build_date/" . $url_params) ?>"
        <?php if(isset($date_range_type) && ($date_range_type == 'build')) { ?> class="selected" <?php } ?>>By Build Date</a>
    </li>
    <?php } ?>
</ul>
