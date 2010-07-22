package com.mozilla.util;

import java.util.Calendar;

public class DateUtil {

	/**
	 * Get the first moment in time for the given time and resolution
	 * @param time
	 * @param resolution
	 * @return
	 */
	public static long getTimeAtResolution(long time, int resolution) {
		Calendar cal = Calendar.getInstance();
		cal.setTimeInMillis(time);
		
		switch (resolution) {
			case Calendar.DATE:
				cal.set(Calendar.HOUR, 0);
			case Calendar.HOUR:
				cal.set(Calendar.MINUTE, 0);
			case Calendar.MINUTE:
				cal.set(Calendar.SECOND, 0);
			case Calendar.SECOND:
				cal.set(Calendar.MILLISECOND, 0);
			default:
				break;
		}
		
		return cal.getTimeInMillis();
	}

	/**
	 * Get the last moment in time for the given time and resolution
	 * @param time
	 * @param resolution
	 * @return
	 */
	public static long getEndTimeAtResolution(long time, int resolution) {
		Calendar cal = Calendar.getInstance();
		cal.setTimeInMillis(time);
		
		switch (resolution) {
			case Calendar.DATE:
				cal.set(Calendar.HOUR, 23);
			case Calendar.HOUR:
				cal.set(Calendar.MINUTE, 59);
			case Calendar.MINUTE:
				cal.set(Calendar.SECOND, 59);
			case Calendar.SECOND:
				cal.set(Calendar.MILLISECOND, 999);
			default:
				break;
		}
		
		return cal.getTimeInMillis();
	}
	
}
