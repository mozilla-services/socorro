.. index:: populate postgres

.. _populatepostgres-chapter:

Populate PostgreSQL
===================

Socorro supports multiple products, each of which may contain multiple versions.

* A product is a global product name, such as Firefox, Thunderbird, Fennec, etc.
* A version is a revision of a particular product, such as Firefox 3.6.6 or Firefox 3.6.5
* A branch is the indicator for the Gecko platform used in a Mozilla product / version. If your crash reporting project does not have a need for branch support, just enter “1.0” as the branch number for your product / version.

Customize CSV files
-------------------

Socorro comes with a set of CSV files you can customize and use to bootstrap
your database.

Shut down all Socorro services, drop your database (if needed) and load 
the schema.
From inside the Socorro checkout, as *postgres* user:
::
  dropdb breakpad # skip this if you haven't created a db yet
  createdb -E 'utf8' -l 'en_US.utf8' -T template0 breakpad
  psql -f sql/schema/2.5/breakpad_roles.sql breakpad
  psql -f sql/schema/2.5/breakpad_schema.sql breakpad

The tables are partitioned by date (http://www.postgresql.org/docs/8.3/static/ddl-partitioning.html), there is a script to create them initial and they 
are maintained by cron afterwards.
From inside the Socorro checkout, as *socorro* user:
::
  cp scripts/config/setupdatabaseconfig.py.dist scripts/config/setupdatabaseconfig.py
  export PYTHONPATH=.:thirdparty
  export PGPASSWORD="aPassword"
  cp scripts/config/createpartitionsconfig.py.dist scripts/config/createpartitionsconfig.py
  python scripts/createPartitions.py

Customize CSVs, at minimum you probably need to bump the dates and build IDs in: 
  raw_adu.csv reports.csv releases_raw.csv

You will probably want to change "WaterWolf" to your own
product name and version history, if you are setting this up for production.

Also, note that the backfill procedure will ignore build IDs over 30 days old.

From inside the Socorro checkout, as the *postgres* user:
::
  cd tools/dataload
  edit *.csv
  ./import.sh

See :ref:`databasetablesbysource-chapter` for a complete explanation
of each table.

Run backfill function to populate matviews
------------------------------------------
Socorro depends upon materialized views which run nightly, to display
graphs and show reports such as "Top Crash By Signature".

IMPORTANT NOTE - many reports use the reports_clean_done() stored
procedure to check that reports exist for the last UTC hour of the
day being processed, as a way to catch problems. If your crash 
volume is low enough, you may want to modify this function 
(it is in breakpad_schema.sql referenced above).

Normally this is run for the previous day by cron_daily_matviews.sh 
but you can simply run the backfill function to bootstrap the system:

This is normally run by the import.sh, so take a look in there if
you need to make adjustments.

There also needs to be at least one featured version, which is
controlled by setting "featured_version" column to "true" for one
or more rows in the product_version table.

Restart memcached as the *root* user:
::
  /etc/init.d/memcached restart

Now the :ref:`ui-chapter` should now work. 

You can change settings using the admin UI, which will be at 
http://crash-stats/admin (or the equivalent hostname for your install.)

Load data via snapshot
----------------------
If you have access to an existing Socorro database snapshot, you can load it like so:
::
  # shut down database users
  sudo /etc/init.d/supervisor force-stop
  sudo /etc/init.d/apache2 stop
  
  # drop old db and load snapshot
  sudo su - postgres
  dropdb breakpad
  createdb -E 'utf8' -l 'en_US.utf8' -T template0 breakpad
  pg_restore -Fc -d breakpad minidb.dump
  
This may take several hours, depending on your hardware. One way to speed this up would be to:

* If in a VirtualBox environment, add more CPU cores to the VM (via virtualbox GUI), default is 1
* Add "-j n" to pg_restore command above, where n is number of CPU cores - 1
