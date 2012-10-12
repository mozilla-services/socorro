<?php
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

echo "Date";
foreach ($versions_in_result as $version) {
	echo "," . $product . " " . $version . " Crashes";
	echo "," . $product . " " . $version . " ADU";
	echo "," . $product . " " . $version . " Throttle";
	echo "," . $product . " " . $version . " Ratio";
}
echo "\n";

foreach ($dates as $date) {
	echo $date;
	echo ",";

	for ($i = 0; count($versions_in_result) > $i; $i++) {
	    if ($versions_in_result[$i] == $versions[$i]) {
	        $key = $versions_in_result[$i];

			if (isset($statistics['versions'][$key][$date]['crashes'])) {
				echo round($statistics['versions'][$key][$date]['crashes']);
			} else {
				echo '-';
			}
			echo ",";

			if (isset($statistics['versions'][$key][$date]['users'])) {
				echo round($statistics['versions'][$key][$date]['users']);
			} else {
				echo '-';
			}
			echo ",";

			if (isset($statistics['versions'][$key][$date]['throttle'])) {
    			echo $statistics['versions'][$key][$date]['throttle'] * 100 . '%';
    		} else {
    			echo '-';
    		}
    		echo ",";

			if (isset($statistics['versions'][$key][$date]['ratio'])) {
				$ratio = round($statistics['versions'][$key][$date]['ratio'] * 100, 2);
				echo $ratio . "%";
			} else {
				echo '-';
			}
			echo ",";
		}
	}
	echo "\n";
}

echo "Total,";

for ($i = 0; count($versions_in_result) > $i; $i++) {
	if ($versions_in_result[$i] == $versions[$i]) {
		$key = $versions_in_result[$i];

		if (isset($statistics['versions'][$key]['crashes'])) {
			echo round($statistics['versions'][$key]['crashes']);
		}
		echo ",";

		if (isset($statistics['versions'][$key]['users'])) {
			echo round($statistics['versions'][$key]['users']);
		}
		echo ",";

    	if (isset($statistics['versions'][$key]['throttle'])) {
    		echo $statistics['versions'][$key]['throttle'] * 100 . '%';
    	}
    	echo ",";

		if (isset($statistics['versions'][$key]['ratio'])) {
			$ratio = round($statistics['versions'][$key]['ratio'] * 100, 2);
			echo $ratio . "%";
		}
		echo ",";
	}
}
echo "\n";
?>
