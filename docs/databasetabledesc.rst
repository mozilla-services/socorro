.. index:: database

.. _databasetabledesc-chapter:

PostgreSQL Database Table Descriptions
======================================

This document describes the various tables in PostgreSQL by their purpose and essentially what data each contains.  This is intended as a reference for socorro developers and analytics users.

Tables which are in the database but not listed below are probably legacy tables which are slated for removal in future Socorro releases.

CURRENTLY IN PROGRESS.  NOT COMPLETE AS OF 2012-02-27

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

reports_user_info
-----------------

Contains a handful of "optional" information from the reports table which is either security-sensitive or is not included in all reports and is large.  This includes the full URL, user email address, comments, and app_notes.   As such, access to this table in production may be restricted.  

Partitioned by date into weekly partitions, so each query against this table should contain a predicate on date_processed.  Relates to reports_clean via UUID, which is also its primary key.

product_adu
------------

The normalized version of raw_adu, contains summarized estimated counts of users for each product-version since Rapid Release began.  Populated by daily cronjob.


Dimensions
==========

* daily_crash_codes
* os_name_matches
* os_names
* process_types
* product_release_channels
* products
* release_channel_matches
* release_channels
* uptime_levels
* windows_versions

addresses
  cron job, part of update_reports_clean based on reports
domains
  cron job, part of update_reports_clean based on reports
flash_versions
  cron job, part of update_reports_clean based on reports
os_versions
  cron job, update_os_versions based on reports@
  cron job, update_reports_clean based on reports
plugins
  populated by processors based on crash data
product_version_builds
  cron job, update_product_versions, based on releases_raw
product_versions
  cron job, update_product_versions, based on releases_raw
reasons
  cron job, update_reports_clean, based on reports
signatures
  cron job, update_signatures, based on reports@
  cron job, update_reports_clean, based on reports

Matviews
========

bug_associations
  not sure
daily_crashes
  daily_crashes based on reports
daily_hangs
  update_hang_report based on reports
signature_products
  update_signatures based on reports@
signature_products_rollup
  update_signatures based on reports@
tcbs
  update_tcbs based on reports


Application Support Tables
==========================
These tables are used by various parts of the application to do other things than reporting.  They are populated/managed by those applications. 

* data processing control tables

	* product_productid_map
	* reports_bad

* email campaign tables 

	* email_campaigns
	* email_campaigns_contacts
	* email_contacts

* processor management tables

	* jobs
	* priorityjobs
	* priority_jobs_*
	* processors
	* server_status

* UI management tables

	* sessions

* monitoring tables

	* replication_test

* cronjob and database management

	* cronjobs
	* report_partition_info
