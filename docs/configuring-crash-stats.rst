.. index:: configuring-crashstats

.. _configuring-crashstats-chapter:

Configuring Crash-Stats and PostgreSQL
======================================

https://crash-stats.mozilla.org is Mozilla's front-end to expose crash-stats
to developers and interested users. It is written with Mozilla's unique 
requirements in mind, and will probably not be useful to other Socorro users.

You probably do not want to use this, unless you are Mozilla.

Install PostgreSQL
------------------

Install the PostgreSQL repository.
::
  sudo rpm -ivh http://yum.postgresql.org/9.3/redhat/rhel-7-x86_64/pgdg-centos93-9.3-1.noarch.rpm

Now you can actually install the packages:
::
  sudo yum install postgresql93-server postgresql93-contrib

Initialize and enable PostgreSQL on startup:
::
  sudo service postgresql-9.3 initdb
  sudo systemctl enable postgresql-9.3

Modify postgresql config
::
  sudo vi /var/lib/pgsql/9.3/data/postgresql.conf

Ensure that timezone is set to UTC
::
  timezone = 'UTC'

Allow local connections for PostgreSQL
::
  sudo vi /var/lib/pgsql/9.3/data/pg_hba.conf

Ensure that local connections are allowed:
::

  # IPv4 local connections:
  host    all             all             127.0.0.1/32            trust
  # IPv6 local connections:
  host    all             all             ::1/128                 trust

See http://www.postgresql.org/docs/9.3/static/auth-pg-hba-conf.html
for more information on this file.

You'll need to restart postgresql if the configuration was updated:
::
  sudo systemctl restart postgresql-9.3

Create database, set up schema
------------------------------

Socorro provides a setup script which attempts to initialize PostgreSQL::

    sudo setup-socorro.sh postgresql

This creates a new database named "breakpad" and sets up the schema
that Socorro and crash-stats expect.

Configure Socorro Processor
---------------------------

::
  socorro processor \
    --destination.crashstorage_class='
      socorro.external.crashstorage_base.PolyCrashStorage' \
    --destination.storage_classes='
      socorro.external.fs.crashstorage.FSLegacyDatedRadixTreeStorage,       
      socorro.external.postgresql.crashstorage.PostgreSQLCrashStorage'


Start services
--------------

Both the Django socorro-webapp and the socorro-middleware REST service
must be running::

    sudo systemctl enable socorro-middleware socorro-webapp

Configure Nginx
---------------

Both socorro-webapp and socorro-middleware should be fronted by a
webserver like Nginx. This is so we can run Socorro components under the
socorro user and not need to listen on privileged port 80, and also to 
protect from slow clients.

You can find a working configs in
/etc/nginx/conf.d/socorro-{webapp,middleware}.conf.sample

You should change server_name in socorro-webapp.conf at minimum, the default is
"crash-stats".

You can leave the default "socorro-middleware" in socorro-middleware.conf

Copy these .sample files to .conf and restart Nginx to activate::

  sudo systemctl restart nginx

Cron jobs
---------

Socorro uses a crontab manager called Crontabber. This needs
to be in /etc/cron.d/socorro on a single host (generally referred to
as the "admin host")::

    */5 * * * * socorro /data/socorro/application/scripts/crons/crontabber.sh

Set up crash-stats web site
---------------------------

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
    export SECRET_KEY="..."
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
  sudo systemctl restart memcached

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

Create partitioned tables
-------------------------

Normally this is handled automatically by the cronjob scheduler
:ref:`crontabber-chapter` but can be run as a one-off:
::
  python socorro/cron/crontabber_app.py --job=weekly-reports-partitions --force

Partitioning and data expiration
--------------------------------

Collecting crashes can generate a lot of data. We have a few tools for
automatically partitioning and discarding data in our data stores.

*PostgreSQL*

For automatic, date-based partitioning, we have crontabber jobs that create
partitions weekly based on data in the table:
::
  report_partition_info

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


Symbols S3 uploads
------------------

The webapp has support for uploading symbols. This can be done by the user
either using an upload form or you can HTTP POST directly in. E.g. with curl.

For this to work you need to configure the S3 bucket details. The file
``webapp-django/crashstats/settings/base.py`` specifies the defaults which
are all pretty much empty.

First of all, you need to configure the AWS credentials. This is done by
overriding the following keys::

    AWS_ACCESS_KEY
    AWS_SECRET_ACCESS_KEY

These settings can not be empty.

Next you have to set up the bucket name. When doing so, if you haven't already
created the bucket over on the AWS console or other management tools you
also have to define the location. The bucket name is set by setting the
following key::

    SYMBOLS_BUCKET_DEFAULT_NAME

And the location is set by setting the following key::

    SYMBOLS_BUCKET_DEFAULT_LOCATION

If you're wondering what the format of the location should be,
you can see `a list of the constants here <http://boto.readthedocs.org/en/latest/ref/s3.html#boto.s3.connection.Location>`_.
For example ``us-west-2``.

If you want to have a different bucket name for different user you can
populate the following setting as per this example:

.. code-block:: python

    SYMBOLS_BUCKET_EXCEPTIONS = {
        'joe.bloggs@example.com': 'private-crashes.my-bucket',
    }

That means that when ``joe.bloggs@example.com`` uploads symbols they are
stored in a different bucket called ``private-crashes.my-bucket``.

If you additionally want to use a different location for this user you
can enter it as a tuple like this:

.. code-block:: python

    SYMBOLS_BUCKET_EXCEPTIONS = {
        'joe.bloggs@example.com': ('private-crashes.my-bucket', 'us-east-1'),
    }
