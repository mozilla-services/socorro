<?php defined('SYSPATH') or die('No direct script access.');

/**
 * 
 */
class TimeUtil {
    /**
     * 
     */
    public static function roundOffByMinutes($minutes, $time=NULL)
    {
	if (is_null($time)) {
	    $time = time();
	}
	$factor = $minutes * 60;
	return round($time / $factor) * $factor;
    }
}
?>