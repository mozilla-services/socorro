Rank, Percentage of All Crashes, Signature, Total, Win, Linux, Mac
<?php foreach ($top_crashers as $topcrash) {
        echo implode(",", $topcrash);
	echo "\n";
      } ?>

