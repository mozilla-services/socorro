.. index:: configuring-socorro

Configuring Socorro
===================

Socorro produces graphs and reports, most are updated once per day.

You must enter information about your releases into Socorro in order
for this to work, and this information must match the incoming crashes.

Becoming a superuser
--------------------

If you're starting a fresh new Socorro instance without any users at
all, you need to bootstrap at least one superuser so the paragraph
above starts to make sense. To do that, you first need to **sign in at
least once** using the email address you want to identify as a
superuser. Once you've done that, run the following command::

    cd /data/socorro
    ./socorro-virtualenv/bin/python webapp-django/manage.py makesuperuser theemail@address.com

Now the user with this email address should see a link to "Admin" in
the footer.

From this point on, you no longer need the command line to add other
superusers - you can do this from http://crash-stats/admin/users/

Adding new products and releases
--------------------------------

Each product you wish to have reports on must be added via the Socorro
admin UI:

http://crash-stats/admin/products/

All products must have one or more releases:

http://crash-stats/admin/releases/

The new releases should be "featured" so they are
used as defaults and show up in all reports:

http://crash-stats/admin/featured-versions/

Make sure to restart memcached so you see your changes right away:
::
  sudo /etc/init.d/memcached restart

Now go to the front page for your application. For example, if your application
was named "KillerApp" then it will appear at:

http://crash-stats/home/products/KillerApp

You should also change the DEFAULT_PRODUCT in local.py (/etc/socorro/local.py
in a packaged install, ./webapp-django/crashstats/settings/local.py otherwise).

Active Daily Install (ADI)
--------------------------

Most graphs and some reports in Socorro depend on having an estimate of
Active Daily Installs for each release, in order to express crashes as a ratio
of crashes per install.

You should insert an ADI number (or estimate) for each day per release into
the raw_adi table in PostgreSQL:
::
  psql breakpad
  -- args: adi_count, date, product_name, product_os_platform,
  --       product_os_version, product_version, build, product_guid,
  --       update_channel
  INSERT INTO raw_adi VALUES (15, '2014-01-01', 'KillerApp', 'Linux', '2.6.18',
                              '1.0', '20140101165243',
                              '{killerapp@example.com}', 'release');

The source of this data is going to be very specific to your application,
you can see how we automate this for crash-stats.mozilla.com in this job:

https://github.com/mozilla/socorro/blob/master/socorro/cron/jobs/fetch_adi_from_hive.py

Partitioning and data expiration
--------------------------------

Collecting crashes can generate a lot of data. We have a few tools for
automatically partitioning and discarding data in our data stores.

*PostgreSQL*

For automatic, date-based partitioning, we have crontabber jobs that create
partitions weekly based on data in the table:
::
  reports_partition_info

We currently manage which tables are partitioned manually by inserting rows into
the production PostgreSQL database.
::
    psql breakpad
    -- Add reports_duplicates table to automatic partitioning
    WITH bo AS (
       SELECT COALESCE(max(build_order) + 1, 1) as number
       FROM report_partition_info
    )
    INSERT into report_partition_info
       (table_name, build_order, keys, indexes, fkeys, partition_column, timetype)
       SELECT 'reports_duplicates', bo.number, '{uuid}',
           '{"date_processed, uuid"}', '{}', 'date_processed', 'TIMESTAMPTZ'
       FROM bo

Tables commonly partitioned include:
::
   reports
   reports_clean
   raw_crashes
   processed_crashes

The partitions are created by the crontabber job WeeklyReportsPartitionsCronApp:

https://github.com/mozilla/socorro/blob/master/socorro/cron/jobs/weekly_reports_partitions.py

This tool can partition based on TIMESTAMPTZ or DATE. The latter is useful for aggregate
reports that become very large over time, like our signature_summary_* reports.

To drop old partitions, the crontabber job DropOldPartitionsCronApp is available:

https://github.com/mozilla/socorro/blob/master/socorro/cron/jobs/drop_old_partitions.py

DropOldPartitionsCronApp currently defaults to dropping old partitions after 1 year.

To truncate old partitions (leave the tables present, but remove data), TruncatePartitionsCronApp
is available:

https://github.com/mozilla/socorro/blob/master/socorro/cron/jobs/truncate_partitions.py

The TruncatePartitionsCronApp is currently written to only truncate data from raw_crashes
and procesesd_crashes, tables that commonly are extremely large. The default is expiration
at 6 months, and this can be overridden easily in configuration.

All of these jobs can be enabled or disabled in crontabber configuration or by modifying
DEFAULT_JOBS in:

https://github.com/mozilla/socorro/blob/master/socorro/cron/crontabber_app.py
