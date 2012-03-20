.. index:: database

.. _databasetabledesc-chapter:

PostgreSQL Database Table Descriptions
======================================

This document describes the various tables in PostgreSQL by their purpose and essentially what data each contains.  This is intended as a reference for socorro developers and analytics users.

Tables which are in the database but not listed below are probably legacy tables which are slated for removal in future Socorro releases.  Certainly if the tables are not described, they should not be used for new features or reports.

Raw Data Tables
===============

These tables hold "raw" data as it comes in from external sources.  As such, these tables are quite large and contain a lot of garbage and data which needs to be conditionally evaluated.  This means that you should avoid using these tables for reports and interfaces unless the data you need isn't available anywhere else -- and even then, you should see about getting the data added to a matview or normalized fact table.

reports
-------

The primary "raw data" table, reports contains the most used information about crashes, one row per crash report.  Primary key is the UUID field.  

The reports table is partitioned by date_processed into weekly partitions, so any query you run against it should include filter criteria (WHERE) on the date_processed column.  Examples:

::

	WHERE date_processed BETWEEN '2012-02-12 11:05:09+07' AND '2012-02-17 11:05:09+07'
	WHERE date_processed >= DATE '2012-02-12' AND date_processed < DATE '2012-02-17'
	WHERE utc_day_is(date_processed, '2012-02-15')
	
Data in this table comes from the processors.

extensions
----------

Contains information on add-ons installed in the user's application.  Currently linked to reports via a synthetic report_id (this will be fixed to be UUID in some future release).  Data is partitioned by date_processed into weekly partitions, so include a filter on date_processed in every query hitting this table.  Has zero to several rows for each crash.

Data in this table comes from the processors.

plugins_reports
---------------

Contains information on some, but not all, installed modules implicated in the crash: the "most interesting" modules.  Relates to dimension table plugins.  Currently linked to reports via a synthetic report_id (this will be fixed to be UUID in some future release).  Data is partitioned by date_processed into weekly partitions, so include a filter on date_processed in every query hitting this table.  Has zero to several rows for each crash.

Data in this table comes from the processors.

bugs
----

Contains lists of bugs thought to be related to crash reports, for linking to crashes.  Populated by a daily cronjob.

bug_associations
----------------

Links bugs from the bugs table to crash signatures.  Populated by daily cronjob.

raw_adu
-------

Contains counts of estimated Average Daily Users as calculated by the Metrics department, grouped by product, version, build, os, and UTC date.  Populated by a daily cronjob.

releases_raw
------------

Contains raw data about Mozilla releases, including product, version, platform and build information.  Populated hourly via FTP-scraping.

reports_duplicates
------------------

Contains UUIDs of groups of crash reports thought to be duplicates according to the current automated duplicate-finding algorithm.  Populated by hourly cronjob.


Normalized Fact Tables
======================

reports_clean
-------------

Contains cleaned and normalized data from the reports table, including product-version, os, os version, signature, reason, and more.  Partitioned by date into weekly partitions, so each query against this table should contain a predicate on date_processed:

::

	WHERE date_processed BETWEEN '2012-02-12 11:05:09+07' AND '2012-02-17 11:05:09+07'
	WHERE date_processed >= DATE '2012-02-12' AND date_processed < DATE '2012-02-17'
	WHERE utc_day_is(date_processed, '2012-02-15')
	
Because reports_clean is much smaller than reports and is normalized into unequivocal relationships with dimenstion tables, it is much easier to use and faster to execute queries against.  However, it excludes data in the reports table which doesn't conform to normalized data, including:

* product versions before the first Rapid Release versions (e.g. Firefox 3.6)
* Camino
* corrupt reports, including ones which indicate a breakpad bug

Populated hourly, 3 hours behind the current time, from data in reports via cronjob.  The UUID column is the primary key.  There is one row per crash report, although some crash reports are suspected to be duplicates.

Columns:

uuid
	artificial unique identifier assigned by the collectors to the crash at collection time.  Contains the date collected plus a random string.

date_processed
	timestamp (with time zone) at which the crash was received by the collectors.  Also the partition key for partitioning reports_clean. Note that the time will be 7-8 hours off for crashes before February 2012 due to a shift from PST to UTC.
	
client_crash_date
	timestamp with time zone at which the users' crashing machine though the crash was happening.  Often innacurrate due to clock issues, is primarily supplied as an anchor timestamp for uptime and install_age.
	
product_version_id
	foreign key to the product_versions table.
	
build
	numeric build identifier as supplied by the client.  Might not match any real build in product_version_builds for a variety of reasons.
	
signature_id
	foreign key to the signatures dimension table.
	
install_age
	time interval between installation and crash, as reported by the client.  To get the reported install date, do ( SELECT client_crash_date - install_age ).
	
uptime
	time interval between program start and crash, as reported by the client.
	
reason_id
	foreign key to the reasons table.
	
address_id
	foreign key to the addresses table.
	
os_name
	name of the OS of the crashing host, for OSes which match known OSes.
	
os_version_id
	foreign key to the os_versions table.
	
hang_id
	UUID assigned to the hang pair grouping for hang pairs.  May not match anything if the hang pair was broken by sampling or lost crash reports.
	
flash_version_id
	foreign key to the flash_versions table
	
process_type
	Crashing process type, linked to process_types dimension.
	
release_channel
	release channel from which the crashing product was obtained, unless altered by the user (this happens more than you'd think).  Note that non-Mozilla builds are usually lumped into the "release" channel.
	
duplicate_of
	UUID of the "leader" of the duplicate group if this crash is marked as a possible duplicate.  If UUID and duplicate_of are the same, this crash is the "leader".  Selection of leader is arbitrary.
	
domain_id
	foreign key to the domains dimension
	
architecture
	CPU architecture of the client as reported (e.g. 'x86', 'arm').
	
cores
	number of CPU cores on the client, as reported.

reports_user_info
-----------------

Contains a handful of "optional" information from the reports table which is either security-sensitive or is not included in all reports and is large.  This includes the full URL, user email address, comments, and app_notes.   As such, access to this table in production may be restricted.  

Partitioned by date into weekly partitions, so each query against this table should contain a predicate on date_processed.  Relates to reports_clean via UUID, which is also its primary key.

product_adu
------------

The normalized version of raw_adu, contains summarized estimated counts of users for each product-version since Rapid Release began.  Populated by daily cronjob.


Dimensions
==========

These tables contain lookup lists and taxonomy for the fact tables in Socorro.  Generally they are auto-populated based on encountering new values in the raw data, on an hourly basis.  A few tables below are manually populated and change extremely seldom, if at all.

Dimensions which are lookup lists of short values join to the fact tables by natural key, although it is not actually necessary to reference them (e.g. os_name, release_channel).  Dimension lists which have long values or are taxonomies or heirarchies join to the fact tables using a surrogate key (e.g. product_version_id, reason_id).

Some dimensions which come from raw crash data have a "first_seen" column which displays when that value was first encountered in a crash and added to the dimension table.  Since the first_seen columns were added in September 2011, most of these will have the value '2011-01-01' which is not meaningful.  Only dates after 2011-09-15 actually indicate a first appearance.

addresses
---------

Contains a list of crash location "addresses", extracted hourly from the raw data.  Surrogate key: address_id.

daily_crash_codes
-----------------

Reference list for the cryptic single-character codes in the daily_crashes table.  Legacy, to be eventually restructured.  Natural key: crash_code.  Manually populated.

domains
-------

List of HTTP domains extracted from raw reports by applying a truncation regex to the crashing URL.  These should contain no personal information.  Contains a "first seen" column.  Surrogate key: domain_id

flash_versions
--------------

List of Abobe Flash version numbers harvested from crashes. Has a "first_seen" column.  Surrogate key: flash_version_id.

os_names
--------

Canonical list of OS names used in Sorocco.  Natural key.  Fixed list, manually populated.

os_versions
-----------

List of versions for each OS based on data harvested from crashes.  Contains some garbage versions because we cannot validate.  Surrogate key: os_version_id.

plugins
-------

List of "interesting modules" harvested from raw crashes, populated by the processors.  Surrogate key: ID.  Links to plugins_reports.

process_types
-------------

Standing list of crashing process types (browser, plugin and hang).  Manually input.  Natural key.

products
--------

List of supported products, along with the first version on rapid release.  Manually maintained.  Natural key: product_name.

product_versions
----------------

Contains a list of versions for each product, since the beginning of rapid release (i.e. since Firefox 5.0).  Version numbers are available expressed several different ways, and there is a sort column for sorting versions.  Also contains build_date/sunset_date visibility information and the featured_version flag.  "build_type" means the same thing as "release_channel".  Surrogate key: product_version_id.

Version columns include:

version_string
	The canonical, complete version number for display to users
	
release_version
	The version number as provided in crash reports (and usually the
	same as the one on the FTP server).  Can be missing suffixes like "b2" or "esr".
	
major_version
	Just the first two numbers of the version number, e.g. "11.0"
	
version_sort
	An alphanumeric string which allows you to sort version numbers in 
	the correct order.
	
beta_number
	The sequential beta release number if the product-version is a beta.
	For "final betas", this number will be 99.


product_version_builds
----------------------

Contains a list of builds for each product-version.  Note that platform information is not at all normalized.  Natural key: product_version_id, build_id.

product_release_channels
------------------------

Contains an intersection of products and release channels, mainly in order to store throttle values.  Manually populated.  Natural key: product_name, release_channel.

reasons
-------

Contains a list of "crash reason" values harvested from raw crashes.  Has a "first seen" column.  Surrogate key: reason_id.

release_channels
----------------

Contains a list of available Release Channels.  Manually populated.  Natural key.  See "note on release channel columns" below.

signatures
----------

List of crash signatures harvested from incoming raw data.  Populated by hourly cronjob.  Has a first_seen column.  Surrogate key: signature_id.

uptime_levels
-------------

Reference list of uptime "levels" for use in reports, primarily the Signature Summary.  Manually populated.

windows_versions
----------------

Reference list of Window major/minor versions with their accompanying common names for reports.  Manually populated.

Matviews
========

These data summaries are derived data from the fact tables and/or the raw data tables.  They are populated by hourly or daily cronjobs, and are frequently regenerated if historical data needs to be corrected.  If these matviews contain the data you need, you should use them first because they are smaller and more efficient than the fact tables or the raw tables.

correlations
------------

Summaries crashes by product-version, os, reason and signature.  Populated
by daily cron job.  Is the root for the other correlations reports.  Correlation reports in the database will not be active/populated until 2.5.2 or later.

correlation_addons
------------------

Contains crash-count summaries of addons per correlation.  Populated by daily cronjob.

correlation_cores
-----------------

Contains crash-count summaries of crashes per architecture and number of cores.  Populated by daily cronjob.

correlation_modules
-------------------

Will contain crash-counts for modules per correlation.  Will be populated daily by pull from Hbase.

daily_crashes
-------------

Stores crash counts per product-version, OS, and day.  This is probably the oldest matview, and has unintuitive and historical column names; it will probably be overhauled or replaced.  The report_type column defines 5 different sets of counts, see daily_crash_codes above.

We recommended that you use the VIEW daily_crash_ratio instead of using daily_crashes, as the structure of daily_crashes is hard to understand and is likely to change in the future.

daily_hangs and hang_report
---------------------------

daily_hangs contains a correlation of hang crash reports with their related hang pair crashes, plus additional summary data.  Duplicates contains an array of UUIDs of possible duplicates.

hang_report is a dynamic view which flattens daily_hangs and its related dimension tables.

nightly_builds 
--------------

contains summaries of crashes-by-age for Nightly and Aurora releases.  Will be populated in Socorro 2.5.1.

product_crash_ratio
-------------------

Dynamic VIEW which shows crashes, ADU, adjusted crashes, and the crash/100ADU ratio, for each product and versions. Recommended for backing graphs and similar.

product_os_crash_ratio
----------------------

Dynamic VIEW which shows crashes, ADU, adjusted crashes, and the crash/100ADU ratio for each product, OS and version.  Recommended for backing graphs and similar.

product_info
------------

dynamic VIEW which suppies the most essential information about each product version for both old and new products.  

signature_products and signature_products_rollup
------------------------------------------------

Summary of which signatures appear in which product_version_ids, with first appearance dates. 

The rollup contains an array-style summary of the signatures with lists of product-versions.

tcbs
----

Short for "Top Crashes By Signature", tcbs contains counts of crashes per day, signature, product-version, and columns counting each OS.

Note On Release Channel Columns
===============================

Due to a historical error, the column name for the Release Channel in various tables may be named "release_channel", "build_type", or "build_channel".  All three of these column names refer to exactly the same thing.  While we regret the confusion, it has not been thought to be worth the refactoring effort to clean it up.  

Application Support Tables
==========================
These tables are used by various parts of the application to do other things than reporting.  They are populated/managed by those applications.   Most are not accessible to the various reporting users, as they do not contain reportable data.

data processing control tables
------------------------------

These tables contain data which supports data processing by the
processors and cronjobs.

product_productid_map
	maps product names based on productIDs, in cases where the product name
	supplied by Breakpad is not correct (i.e. FennecAndroid).
	
reports_bad
	contains the last day of rejected UUIDs for copying from reports to
	reports_clean.  intended for auditing of the reports_clean code.
	
os_name_matches
	contains regexs for matching commonly found OS names in crashes with
	canonical OS names.
	
release_channel_matches
	contains LIKE match strings for release channels for channel names 
	commonly found in crashes with canonical names.
	
special_product_platforms
	contains mapping information for rewriting data from FTP-scraping
	to have the correct product and platform.  Currently used only 
	for Fennec.
	
transform_rules
	contains rule data for rewriting crashes by the processors.  May be
	used in the future for other rule-based rewriting by other components.

email campaign tables 
---------------------

These tables support the application which emails crash reporters with
follow-ups.  As such, access to these tables will restricted.

	* email_campaigns
	* email_campaigns_contacts
	* email_contacts

processor management tables
---------------------------

These tables are used to coordinate activities of the up-to-120 processors 
and the monitor.  

jobs
	The current main queue for crashes waiting to be processed.

priorityjobs
	The queue for user-requested "priority" crash processing.
	
processors
	The registration list for currently active processors.
	
server_status
	Contains summary statistics on the various processor servers.
	
	
UI management tables
--------------------

sessions
	contains session information for people logged into the administration
	interface for Socorro.
	
monitoring tables
-----------------

replication_test
	Contains a timestamp for ganglia to measure the speed of replication.

cronjob and database management
-------------------------------

These tables support scheduled tasks which are run in Socorro.

cronjobs
	contains last-completed and success/failure status for each cronjob
	which affects the database.  Currently does not include all cronjobs.

report_partition_info
	contains configuration information on how the partitioning cronjob
	needs to partition the various partitioned database tables.
	
socorro_db_version
	contains the socorro version of the current database.  updated by the
	upgrade scripts.
	
socorro_db_version_history
	contains the history of version upgrades of the current database.
	

	
