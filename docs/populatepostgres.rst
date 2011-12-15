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
  psql -f sql/schema/2.3/breakpad_schema.sql

From inside the Socorro checkout, as the *postgres* user:
::
  cd tools/dataload
  edit *.csv
  ./import.sh

See :ref:`databasetablesbysource-chapter` for a complete explanation
of each table.

Run nightly aggregate cron job
------------
The "newtcbs" job should be run nightly, and generates all aggregate
reports ("Top Crashes By Signature", graphs, etc) for the previous day.

Run it once by hand to bootstrap the system:

As the *socorro* user:
::
  bash /data/socorro/application/scripts/crons/cron_newtcbs.sh 

Logs will be written to /var/log/socorro/cron_newtcbs.log


Enable at least one "featured" product
------------

As *postgres* user:
::
  psql -h localhost -U breakpad_rw breakpad
  UPDATE product_versions SET featured_version = true WHERE product_version_id = 1;

The :ref:`ui-chapter` should now work. You can change settings using the admin
UI, which will be at http://crash-stats/admin (or the equivalent hostname for
your install.)
