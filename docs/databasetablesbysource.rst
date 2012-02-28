.. index:: database

.. _databasetablesbysource-chapter:

PostgreSQL Database Tables by Data Source
=========================================

Last updated: 2011-01-15

This document breaks down the tables in the Socorro PostgreSQL database by where their data comes from, rather than by what the table contains.  This is a prerequisite to populating a brand-new socorro database or creating synthetic testing workloads.

Manually Populated Tables
=========================

The following tables have no code to populate them automatically.  Initial population and any updating need to be done by hand.  Generally there's no UI, either; use queries.

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
* product_productid_map
* report_partition_info

Tables Receiving External Data
==============================

These tables actually get inserted into by various external utilities.  This is most of our "incoming" data.

bugs
	list of bugs, populated by bugzilla-scraper
extensions
	populated by processors
plugins_reports
	populated by processors
raw_adu
	populated by daily batch job from metrics
releases_raw
	populated by daily FTP-scraper
reports
	populated by processors


Automatically Populated Reference Tables
========================================

Lookup lists and dimension tables, populated by cron jobs and/or processors based on the above tables.  Most are annotated with the job or process which populates them.  Where the populating process is marked with an @, that indicates a job which is due to be phased out.

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
reports_bad
  cron job, update_reports_clean, based on reports
  future cron job to delete data from this table
signatures
  cron job, update_signatures, based on reports@
  cron job, update_reports_clean, based on reports

Matviews
========

Reporting tables, designed to be called directly by the mware/UI/reports.  Populated by cron job batch.  Where populating functions are marked with a @, they are due to be replaced with new jobs.

bug_associations
  not sure
daily_crashes
  daily_crashes based on reports
daily_hangs
  update_hang_report based on reports
os_signature_counts
  update_os_signature_counts based on reports
product_adu
  daily_adu based on raw_adu
product_signature_counts
  update_product_signature_counts based on reports
reports_clean
  update_reports_clean based on reports
reports_user_info
  update_reports_clean based on reports
reports_duplicates
  find_reports_duplicates based don reports
signature_bugs_rollup
  not sure
signature_first@
  update_signatures based on reports@
signature_products
  update_signatures based on reports@
signature_products_rollup
  update_signatures based on reports@
tcbs
  update_tcbs based on reports
uptime_signature_counts
  update_uptime_signature_counts based on reports

Application Management Tables
=============================

These tables are used by various parts of the application to do other things than reporting.  They are populated/managed by those applications.

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

Deprecated Tables
=================

These tables are supporting functionality which is scheduled to be removed over the next few versions of Socorro. As such, we are ignoring them.

* alexa_topsites
* builds
* frames
* osdims
* priorityjobs_log
* priorityjobs_logging_switch
* product_visibility
* productdims
* productdims_version_sort
* release_build_type_map
* signature_build
* signature_productdims
* top_crashes_by_signature
* top_crashes_by_url
* top_crashes_by_url_signature
* urldims
