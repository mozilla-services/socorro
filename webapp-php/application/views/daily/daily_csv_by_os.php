<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

echo "Date";
foreach ($statistics['os'] as $os) {
	echo "," . $product . " " . $versions[0] . " on " . $os . " Crashes";
	echo "," . $product . " " . $versions[0] . " on " . $os . " ADU";
	echo "," . $product . " " . $versions[0] . " on " . $os . " Throttle";
	echo "," . $product . " " . $versions[0] . " on " . $os . " Ratio";
}
echo "\n";

foreach ($dates as $date) {
	echo $date;
	echo ",";

	foreach ($operating_systems as $operating_system) {
		if (isset($statistics['os'][$operating_system][$date]['crashes'])) {
			echo round($statistics['os'][$operating_system][$date]['crashes']);
		} else {
			echo '-';
		}
		echo ",";

		if (isset($statistics['os'][$operating_system][$date]['users'])) {
			echo round($statistics['os'][$operating_system][$date]['users']);
		} else {
			echo '-';
		}
		echo ",";

		if (isset($statistics['os'][$operating_system][$date]['throttle'])) {
			echo $statistics['os'][$operating_system][$date]['throttle'] * 100 . '%';
		} else {
			echo '-';
		}
		echo ",";

		if (isset($statistics['os'][$operating_system][$date]['ratio'])) {
			$ratio = round($statistics['os'][$operating_system][$date]['ratio'] * 100, 2);
			echo $ratio . "%";
		} else {
			echo '-';
		}
		echo ",";
	}
	echo "\n";
}

echo "Total,";

$i = 0;
foreach($operating_systems as $operating_system) {
	if (isset($statistics['os'][$operating_system]['crashes'])) {
		echo round($statistics['os'][$operating_system]['crashes']);
	}
	echo ",";

	if (isset($statistics['os'][$operating_system]['users'])) {
		echo round($statistics['os'][$operating_system]['users']);
	}
	echo ",";

	if (isset($statistics['os'][$operating_system]['throttle'])) {
		echo $statistics['os'][$operating_system]['throttle'] * 100;
	}
	echo ",";

	if (isset($statistics['os'][$operating_system]['ratio'])) {
		$ratio = round($statistics['os'][$operating_system]['ratio'] * 100, 2);
		echo $ratio . "%";
	}
	echo ",";
}
echo "\n";
?>
