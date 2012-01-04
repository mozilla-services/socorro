.. index:: populate postgres

.. _populatepostgres-chapter:

Populate PostgreSQL
============

Socorro supports multiple products, each of which may contain multiple versions.

* A product is a global product name, such as Firefox, Thunderbird, Fennec, etc.
* A version is a revision of a particular product, such as Firefox 3.6.6 or Firefox 3.6.5
* A branch is the indicator for the Gecko platform used in a Mozilla product / version. If your crash reporting project does not have a need for branch support, just enter “1.0” as the branch number for your product / version.

Customize CSV files
------------

Socorro comes with a set of CSV files you can customize and use to bootstrap
your database.

Shut down all Socorro services, drop your database (if needed) and load 
the schema.
From inside the Socorro checkout, as *postgres* user:
::
  dropdb breakpad # skip this if you haven't created a db yet
  createdb -E 'utf8' -l 'en_US.utf8' -T template0 breakpad
  psql -f sql/schema/2.3/breakpad_roles.sql breakpad
  psql -f sql/schema/2.3/breakpad_schema.sql breakpad

From inside the Socorro checkout, as the *postgres* user:
::
  cd tools/dataload
  # customize CSVs, at minimum you need to
  # bump the dates in raw_adu.csv reports.csv signatures.csv
  edit *.csv
  ./import.sh

See :ref:`databasetablesbysource-chapter` for a complete explanation
of each table.

Run backfill function to populate matviews
------------
Socorro depends upon materialized views which run nightly, to display
graphs and show reports such as "Top Crash By Signature".

Normally this is run for the previous day by cron_daily_matviews.sh 
but you can simply run the backfill function to bootstrap the system:

As the *postgres* user:
::
  psql -h localhost -U breakpad_rw breakpad
  breakpad=# select backfill_matviews('2012-01-03', '2012-01-03');

Be sure to use to/from dates that match the CSV data you have entered.
There should be no failures, and the result should be "true".

Enable at least one "featured" product, this command will set all 
current versions to "featured" (this controls which versions appear on the
front page of the web UI):
::
  breakpad=# UPDATE product_versions SET featured_version = true;

Restart memcached as the *root* user:
::
  /etc/init.d/memcached restart

Now the :ref:`ui-chapter` should now work. 

You can change settings using the admin UI, which will be at 
http://crash-stats/admin (or the equivalent hostname for your install.)
