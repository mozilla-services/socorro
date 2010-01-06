<?php 

echo "Date";
foreach ($statistics['versions'] as $key => $version) {
	echo "," . $product . " " . $key . " Crashes";
	echo "," . $product . " " . $key . " 1k ADU";
	echo "," . $product . " " . $key . " Ratio";
} 
echo "\n";

foreach ($dates as $date) {
	echo $date; 
	echo ",";
	
	$i = 0;
	foreach ($results->versions as $version) { 
		if ($version->version == $versions[$i]) {
			$key = $version->version;

			if (isset($statistics['versions'][$key][$date]['crashes'])) {
				echo $statistics['versions'][$key][$date]['crashes']; 
			} else {
				echo '-';
			}
			echo ",";
			
			if (isset($statistics['versions'][$key][$date]['users'])) {
				echo $statistics['versions'][$key][$date]['users'] / 1000; 
			} else {
				echo '-';
			}
			echo ",";
			
			if (isset($statistics['versions'][$key][$date]['ratio'])) {
				$ratio = round($statistics['versions'][$key][$date]['ratio'] * 100, 3);
				if ($ratio == 0.000 && $statistics['versions'][$key][$date]['crashes'] > 0) {
					echo '0.001';
				} elseif ($ratio == 0) {
					echo '0.000';
				} else {
					echo $ratio;
				}
				echo "%";
			} else {
				echo '-';
			}
			echo ",";
	
			$i++;
		}	
	}
	echo "\n";
}

echo "Total,";

$i = 0;
foreach($results->versions as $version) { 
	if ($version->version == $versions[$i]) {
		$key = $version->version;

		if (isset($statistics['versions'][$key]['crashes'])) {
			echo $statistics['versions'][$key]['crashes']; 
		}
		echo ",";

		if (isset($statistics['versions'][$key]['users'])) {
			echo $statistics['versions'][$key]['users'] / 1000; 
		}
		echo ",";

		if (isset($statistics['versions'][$key]['ratio'])) {
			$ratio = round($statistics['versions'][$key]['ratio'] * 100, 3);
			if ($ratio == 0.000 && $statistics['versions'][$key]['crashes'] > 0) {
				echo '0.001';
			} elseif ($ratio == 0) {
				echo '0.000';
			} else {
				echo $ratio;
			}
			echo "%"; 
		}
		echo ",";
	}
	$i++;
}
echo "\n";
?>
