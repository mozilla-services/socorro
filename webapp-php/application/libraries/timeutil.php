<?php defined('SYSPATH') or die('No direct script access.');

/**
 * A collection of time / date utilities.
 */
class TimeUtil {

    /**
     * Round a timestamp to X minutes.
 	 * 
	 * @param 	int 	The desired number of minutes to round to.
	 * @param 	int 	The timestamp to round
	 * @return 	int 	The  	
     */
    public static function roundOffByMinutes($minutes, $time=NULL)
    {
	if (is_null($time)) {
	    $time = time();
	}
	$factor = $minutes * 60;
	return round($time / $factor) * $factor;
    }

	/**
	 * Determine the day differential between 2 date strings.  Using strtotime()
	 * which allows a variety of date strings to be used.
	 *
	 * @access public
	 * @param 	string 	The $start_date
	 * @param 	string 	The $end_date
	 * @param 	int 	The number of days 
	 */
	public static function determineDayDifferential ($start_date, $end_date)
	{
		$start_time = strtotime($start_date);
		$end_time = strtotime($end_date);
		if (is_numeric($start_time) && is_numeric($end_time)) {
			$differential = $end_time - $start_time;
			if ($differential > 0) {
				return round($differential / 86400);
			}
		}
		return false;
	}
	
	/**
	 * Determine the hour differential between 2 date strings.  Using strtotime()
	 * which allows a variety of date strings to be used.
	 *
	 * @access public
	 * @param 	string 	The $start_date
	 * @param 	string 	The $end_date
	 * @param 	int 	The number of hours 
	 */
	public static function determineHourDifferential ($start_date, $end_date)
	{
		$start_time = strtotime($start_date);
		$end_time = strtotime($end_date);
		if (is_numeric($start_time) && is_numeric($end_time)) {
			$differential = $end_time - $start_time;
			if ($differential > 0) {
				return round($differential / 3600);
			}
		}
		return false;
	}

}
?>