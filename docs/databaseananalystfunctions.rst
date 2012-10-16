.. index:: database

.. _databaseanalystfunctions-chapter:

Database Analyst Functions and Views Reference
==============================================

This doc covers views and functions which are designed for direct use
by analyst and metrics teams pulling data straight from the database.

product_crash_ratio (view)
---------------------------

Dynamic VIEW which shows crashes, ADU, adjusted crashes, and the crash/100ADU ratio, for each product and versions. Recommended for backing graphs and similar.

product_os_crash_ratio (view)
-----------------------------

Dynamic VIEW which shows crashes, ADU, adjusted crashes, and the crash/100ADU ratio for each product, OS and version.  Recommended for backing graphs and similar.

stability_report (function)
---------------------------

Purpose: supplies crash count data in a variety of configurable groupings to allow
	crash-kill staff to populate the daily or weekly stability reports.

Called By: Crash-Kill stability report generator, daily or weekly.

::

	stability_report(
		start_date DATE,
		end_date DATE,
		products ARRAY of TEXT default EMPTY
		groups ARRAY of TEXT default 'product'
	)

	RETURNS TABLE
		report_date : UTC day of crash report
		product : product name
		channel : release channel
		version : full version string, e.g. "17.0b2"
		os_name : long name of the OS, eg. "Windows"
		crash_type : crash type from the Crashes-by-User UI
		report_count : adjusted report count
		adu : active daily installs
		crash_hadu : crashes per 100 active daily installs

Parameters:

start_date
	UTC date of first crash report, inclusive
end_date
	UTC date of last crash report, inclusive
products
	array of products to filter by.  Default is not to filter by product.
groups
	array of columns to group by (in addition to report_date).  Default is to
	group by product name only.  Available columns for grouping are: product,
	channel, version, os_name, crash_type.  The order in which you list the columns
	is also the order in which they will be sorted.

Usage examples:

Return crash totals from October 11 to October 12, inclusive, grouped by product for
all products:

::

	SELECT * FROM stability_report('2012-10-11','2012-10-12');

Get crash totals for all products on October 12, not grouped by product.
The '{}' notation indicates a deliberately empty array:

::

	SELECT * FROM stability_report( start_date := '2012-10-12', end_date := '2012-10-12',
		groups := '{}');


Get crash totals from October 11 to 12 for Firefox and FennecAndroid,
grouped by product, channel and version, sorted by product, then channel, then version.

::

	SELECT * FROM stability_report('2012-10-11','2012-10-12',
	ARRAY['Firefox','FennecAndroid'],ARRAY['product','channel','version']);

Get crash totals from October 11 to 12 for Firefox and Thunderbird,
grouped by product and os_name, sorted by os_name, then product.

::

	SELECT * FROM stability_report('2012-10-11','2012-10-12',
	ARRAY['Firefox','Thunderbird'],ARRAY['os_name','product']);


Notes:
* report_count is the adjusted report count, which means Firefox release
    versions are multiplied by 10 to compensate for throttling.
* rapid betas, when they come in the future, will be reported as the same "version" for all beta releases.
* except for report_date, any column which is not grouped on will also be blank.
* this pulls from crashes_by_user, which stops aggregating crashes for products released more than two years ago.
* crash_hadu for "Unknown" OS is unreasonably large.  This is a known issue due to underlying data issues.
