.. index:: populate postgres

.. _populatepostgres-chapter:

Populate PostgreSQL for the first time
======================================

Socorro supports multiple products, each of which may contain multiple versions.

* A product is a global product name, such as Firefox, Thunderbird, Fennec, etc.
* A version is a revision of a particular product, such as Firefox 3.6.6 or Firefox 3.6.5
* A branch is the indicator for the Gecko platform used in a Mozilla product / version. If your crash reporting project does not have a need for branch support, just enter “1.0” as the branch number for your product / version.

Customize CSV files
-------------------

Socorro comes with a set of CSV files you can customize and use to bootstrap
your database.

Load the Socorro schema
::
  ./socorro/external/postgresql/setupdb_app.py --database_name=breakpad

Customize CSVs in tools/dataload/, at minimum you probably need to bump the dates and build IDs in
::
  raw_adu.csv reports.csv releases_raw.csv

You will probably want to change "WaterWolf" to your own
product name and version history, if you are setting this up for production.

See :ref:`databasetablesbysource-chapter` for a complete explanation
of each table.

Run backfill function to populate matviews
------------------------------------------
Socorro depends upon materialized views which run nightly, to display
graphs and show reports such as "Top Crash By Signature".

IMPORTANT NOTE - many reports use the reports_clean_done() stored
procedure to check that reports exist for the last UTC hour of the
day being processed, as a way to catch problems. If your crash 
volume does not guarantee one crash per hour, you may want to modify
this function in socorro/sql/schema.sql and reload the schema
::

  ./socorro/external/postgresql/setupdb_app.py --database_name=breakpad --dropdb

ALSO - the backfill procedure ignores any data over 30 days old.
Make sure you've adjusted the dates in the CSV files appropriately,
or change these funtions in the schema.sql and reload the schema as above.

Normally this is run for the previous day by cron_daily_matviews.sh 
but you can simply run the backfill_matviews() function to bootstrap the system.

This is normally run by the import.sh, so take a look in there if
you need to make adjustments.

There also needs to be at least one featured version, which is
controlled by setting "featured_version" column to "true" for one
or more rows in the product_version table. The import script will go
ahead and set all imported versions as featured.

After modifying CSV files, use the import script to load the data
::
  ./tools/dataload/import.sh
