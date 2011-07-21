<?php defined('SYSPATH') or die('No direct script access.');

/**
 * A collection of time / date utilities.
 */
class TimeUtil {

    /**
     * Round a timestamp to X minutes.
     * 
     * @param   int     The desired number of minutes to round to.
     * @param   int     The timestamp to round
     * @return  int     The     
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
     * @param   string  The $start_date
     * @param   string  The $end_date
     * @param   int     The number of days 
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
     * @param   string  The $start_date
     * @param   string  The $end_date
     * @param   int     The number of hours 
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

    /**
     * Gives a useful hint as to how long a certain amount
     * of seconds were in a human readable format.
     *
     * WARNING: Dead simple, not L10n ready or general purpose.
     * Doesn't handle plurals, etc.
     *
     * @param $seconds integer Number of seconds
     * @return string Empty string for seconds, "$x minutes", etc 
     *                based on timescale
     */
    public static function time_ago_in_words($seconds)
    {
	$seconds = intval($seconds);
        $three_minutes = 3 * 60;
	$one_hour = 60 * 60;
	$one_day = $one_hour * 24;
	$one_week = $one_day * 7;
	$one_month = $one_day * 29;

        if ($seconds < 60) {
	    return "$seconds seconds";
	} else if ($seconds < $one_hour) {
	    return sprintf("%.1f minutes", $seconds / 60);
	} else if ($seconds < $one_day) {
	    return sprintf("%.1f hours", $seconds / $one_hour);
	} else if ($seconds < $one_week) {
	    return sprintf("%.1f days", $seconds / $one_day);
	} else if ($seconds < $one_month * 3) {
	    return sprintf("%.1f weeks", $seconds / $one_week);
	} else {
            return 'more than 3 months';
	}
    }
}
?>
