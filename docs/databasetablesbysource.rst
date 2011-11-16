.. index:: database

.. _databasetablesbysource-chapter:

PostgreSQL Database Tables by Data Source
=========================================

Last updated: 2011-11-11

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

Lookup lists and dimension tables, populated by cron jobs and/or processors based on the above tables. 

* addresses
* domains
* flash_versions
* os_versions
* plugins
* product_version_builds
* product_versions
* reasons
* reports_bad
* signatures

Matviews
========

Reporting tables, designed to be called directly by the mware/UI/reports.  Populated by cron job batch.

* bug_associations
* daily_crashes
* daily_hangs
* os_signature_counts
* product_adu
* product_signature_counts
* reports_clean
* reports_user_info
* reports_duplicates
* signature_bugs_rollup
* signature_first
* signature_products
* signature_products_rollup
* tcbs
* uptime_signature_counts

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

Depreciated Tables
==================

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