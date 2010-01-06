<?php 

echo "Date";
foreach ($statistics['os'] as $key => $os) {
	echo "," . $product . " " . $versions[0] . " on " . $key . " Crashes";
	echo "," . $product . " " . $versions[0] . " on " . $key . " 1k ADU";
	echo "," . $product . " " . $versions[0] . " on " . $key . " Ratio";
} 
echo "\n";

foreach ($dates as $date) {
	echo $date; 
	echo ",";
	
	foreach ($operating_systems as $operating_system) { 
		if (isset($statistics['os'][$operating_system][$date]['crashes'])) {
			echo $statistics['os'][$operating_system][$date]['crashes']; 
		} else {
			echo '-';
		}
		echo ",";
		
		if (isset($statistics['os'][$operating_system][$date]['users'])) {
			echo $statistics['os'][$operating_system][$date]['users'] / 1000; 
		} else {
			echo '-';
		}
		echo ",";
		
		if (isset($statistics['os'][$operating_system][$date]['ratio'])) {
			$ratio = round($statistics['os'][$operating_system][$date]['ratio'] * 100, 3);
			if ($ratio == 0.000 && $statistics['os'][$operating_system][$date]['crashes'] > 0) {
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
	}
	echo "\n";
}

echo "Total,";

$i = 0;
foreach($operating_systems as $operating_system) { 
	if (isset($statistics['os'][$operating_system]['crashes'])) {
		echo $statistics['os'][$operating_system]['crashes']; 
	}
	echo ",";
	
	if (isset($statistics['os'][$operating_system]['users'])) {
		echo $statistics['os'][$operating_system]['users'] / 1000; 
	}
	echo ",";
	
	if (isset($statistics['os'][$operating_system]['ratio'])) {
		$ratio = round($statistics['os'][$operating_system]['ratio'] * 100, 3);
		if ($ratio == 0.000 && $statistics['os'][$operating_system]['crashes'] > 0) {
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
echo "\n";
?>
