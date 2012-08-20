<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
?>
<div class="page-heading">
	<h2 id="homepage-heading">
        <?php
            out::H($product);
            if(isset($version) && !empty($version)) {
                out::H($version);
            }
        ?> Crash Data
    </h2>
 	<ul id="duration" class="options">
        	<li><a href="<?php out::H($url_base); ?>?duration=3">3 days</a></li>
        	<li><a href="<?php out::H($url_base); ?>?duration=7" class="selected">7 days</a></li>
        	<li><a href="<?php out::H($url_base); ?>?duration=14">14 days</a></li>
        </ul>

    <ul id="date-range-type" class="options">
        <li>Date Range:</li>
        <li><a href="<?php out::H($url_base); ?>?date_range_type=report" class="selected">By Crash Date</a></li>
        <li><a href="<?php out::H($url_base); ?>?date_range_type=build">By Build Date</a></li>
    </ul>
</div>

<div id="homepage-graph" class="panel">
    <div class="title">
        <h2>Crashes per 100  Active Daily Users</h2>
    </div>

    <div class="body">
        <div id="adu-chart"></div>
    </div>
</div>

<div class="panel">
    <div class="title">
        <h2>Crash Reports</h2>
    </div>

    <div class="body">
        <div id="release_channels"></div>
    <br class="clear" />
    </div>
</div>
<br class="clear" />
