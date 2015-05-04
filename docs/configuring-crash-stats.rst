.. index:: configuring-crashstats

.. _configuring-crashstats-chapter:

Configuring Crash-Stats and PostgreSQL
======================================

You probably do not want to use this, unless you have *very* similar requirements
to Mozilla. Try using Kibana instead.

https://crash-stats.mozilla.org is Mozilla's front-end to expose crash data
to developers and interested users.

Some of the unique features it provides are:

* public view of crash reports, with private data redacted
* ability to assign users fine-grained permissions to private data
* graphs and reports showing crashes per Active Daily Install (ADI)
* ability to ingest Mozilla release engineering metadata
* Bugzilla integration
* extensive support for the Firefox rapid release cycle

All of these features are baked in and are not trivial to disable or adjust.

Again, if you are not Mozilla you almost certainly would be happier without
using the crash-stats frontend.

Install Memcached
-----------------

crash-stats makes heavy use of memcached::

  sudo yum install memcached
  sudo systemctl enable memcached
  sudo systemctl start memcached

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
  sudo /usr/pgsql-9.3/bin/postgresql93-setup initdb
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

The Mozilla-specific processor ruleset must be used, in order to populate PostgreSQL in a way that crash-stats expects::

  curl -s -X PUT -d "socorro.processor.mozilla_processor_2015.MozillaProcessorAlgorithm2015" localhost:8500/v1/kv/socorro/processor/processor.processor_class

Also, Socorro Processor must be configured to store crashes in Elasticsearch
as well as PostgreSQL::

  curl -s -X PUT -d "socorro.external.postgresql.crashstorage.PostgreSQLCrashStorage, socorro.external.es.crashstorage.ESCrashStorage, socorro.external.fs.crashstorage.FSTemporaryStorage" localhost:8500/v1/kv/socorro/processor/destination.storage_classes
  curl -s -X PUT -d "socorro.external.crashstorage_base.PolyCrashStorage" localhost:8500/v1/kv/socorro/processor/destination.crashstorage_class
  curl -s -X PUT -d "socorro.external.postgresql.crashstorage.PostgreSQLCrashStorage" localhost:8500/v1/kv/socorro/processor/destination.storage1.crashstorage_class
  curl -s -X PUT -d "socorro.external.es.crashstorage.ESCrashStorage" localhost:8500/v1/kv/socorro/processor/destination.storage1.crashstorage_class
  curl -s -X PUT -d "socorro.external.fs.crashstorage.FSTemporaryStorage" localhost:8500/v1/kv/socorro/processor/destination.storage2.crashstorage_class

Make sure to set these in a "common" namespace so they can be used by other apps
later, such as the Socorro Middleware.

NOTE - variables surrounded by @@@ are placeholders and need to be filled in appropriately for your install::

  curl -s -X PUT -d "@@@DATABASE_HOSTNAME@@@" localhost:8500/v1/kv/socorro/common/resource.postgresql.database_hostname
  curl -s -X PUT -d "@@@DATABASE_USERNAME@@@" localhost:8500/v1/kv/socorro/common/secrets.postgresql.database_username
  curl -s -X PUT -d "@@@DATABASE_PASSWORD@@@" localhost:8500/v1/kv/socorro/common/secrets.postgresql.database_password


Configure Socorro-Middleware
----------------------------

Socorro Middlware is a REST service that listens on localhost and should 
*not* be exposed to the outside::

  curl -s -X PUT -d "psql: socorro.external.postgresql, fs: socorro.external.filesystem, es: socorro.external.es, http: socorro.external.http, rabbitmq: socorro.external.rabbitmq" localhost:8500/v1/kv/socorro/middleware/implementations.implementation_list
  curl -s -X PUT -d "CrashData: fs, Correlations: http, CorrelationsSignatures: http, SuperSearch: es, Priorityjobs: rabbitmq, Search: es, Query: es" localhost:8500/v1/kv/socorro/middleware/implementations.service_overrides
  curl -s -X PUT -d "socorro.external.es.connection_context.ConnectionContext" localhost:8500/v1/kv/socorro/middleware/elasticsearch.elasticsearch_class
  curl -s -X PUT -d "socorro.webapi.servers.WSGIServer" localhost:8500/v1/kv/socorro/middleware/web_server.wsgi_server_class

Configure Crash-Stats
---------------------

The crash-stats Django app runs under envconsul, and expects at least the
following environment variables to be set.

These should be set via Consul in the "socorro/webapp-django" prefix,
for instance.

NOTE - variables surrounded by @@@ are placeholders and need to be filled in appropriately for your install::

  curl -s -X PUT -d "@@@ALLOWED_HOSTS@@@" localhost:8500/v1/kv/socorro/webapp-django/ALLOWED_HOSTS
  curl -s -X PUT -d "http://localhost" localhost:8500/v1/kv/socorro/webapp-django/MWARE_BASE_URL
  curl -s -X PUT -d "socorro-middleware" localhost:8500/v1/kv/socorro/webapp-django/MWARE_HTTP_HOST
  curl -s -X PUT -d "True" localhost:8500/v1/kv/socorro/webapp-django/CACHE_MIDDLEWARE
  curl -s -X PUT -d "False" localhost:8500/v1/kv/socorro/webapp-django/CACHE_MIDDLEWARE_FILES
  curl -s -X PUT -d "@@@DEFAULT_PRODUCT@@@" localhost:8500/v1/kv/socorro/webapp-django/DEFAULT_PRODUCT
  curl -s -X PUT -d "django.core.cache.backends.memcached.MemcachedCache" localhost:8500/v1/kv/socorro/webapp-django/CACHE_BACKEND
  curl -s -X PUT -d "@@@CACHE_LOCATION@@@" localhost:8500/v1/kv/socorro/webapp-django/CACHE_LOCATION
  curl -s -X PUT -d "@@@CACHE_KEY_PREFIX@@@" localhost:8500/v1/kv/socorro/webapp-django/CACHE_KEY_PREFIX
  curl -s -X PUT -d "@@@BROWSERID_AUDIENCES@@@" localhost:8500/v1/kv/socorro/webapp-django/BROWSERID_AUDIENCES
  curl -s -X PUT -d "django.db.backends.postgresql_psycopg2" localhost:8500/v1/kv/socorro/webapp-django/DATABASE_ENGINE
  curl -s -X PUT -d "@@@DATABASES_NAME@@@" localhost:8500/v1/kv/socorro/webapp-django/DATABASE_NAME
  curl -s -X PUT -d "@@@DATABASES_USER@@@" localhost:8500/v1/kv/socorro/webapp-django/DATABASE_USER
  curl -s -X PUT -d "@@@DATABASES_PASSWORD@@@" localhost:8500/v1/kv/socorro/webapp-django/DATABASE_PASSWORD
  curl -s -X PUT -d "@@@DATABASES_HOST@@@" localhost:8500/v1/kv/socorro/webapp-django/DATABASE_HOST
  curl -s -X PUT -d "@@@DATABASES_PORT@@@" localhost:8500/v1/kv/socorro/webapp-django/DATABASE_PORT
  curl -s -X PUT -d "True" localhost:8500/v1/kv/socorro/webapp-django/SESSION_COOKIE_SECURE
  curl -s -X PUT -d "True" localhost:8500/v1/kv/socorro/webapp-django/COMPRESS_OFFLINE
  curl -s -X PUT -d "@@@SECRET_KEY@@@" localhost:8500/v1/kv/socorro/webapp-django/SECRET_KEY
  curl -s -X PUT -d "@@@GOOGLE_ANALYTICS_ID@@@" localhost:8500/v1/kv/socorro/webapp-django/GOOGLE_ANALYTICS_ID
  curl -s -X PUT -d "@@@DATASERVICE_DATABASE_USERNAME@@@" localhost:8500/v1/kv/socorro/webapp-django/DATASERVICE_DATABASE_USERNAME
  curl -s -X PUT -d "@@@DATASERVICE_DATABASE_PASSWORD@@@" localhost:8500/v1/kv/socorro/webapp-django/DATASERVICE_DATABASE_PASSWORD
  curl -s -X PUT -d "@@@DATASERVICE_DATABASE_HOSTNAME@@@" localhost:8500/v1/kv/socorro/webapp-django/DATASERVICE_DATABASE_HOSTNAME
  curl -s -X PUT -d "@@@DATASERVICE_DATABASE_NAME@@@" localhost:8500/v1/kv/socorro/webapp-django/DATASERVICE_DATABASE_NAME
  curl -s -X PUT -d "@@@DATASERVICE_DATABASE_PORT@@@" localhost:8500/v1/kv/socorro/webapp-django/DATASERVICE_DATABASE_PORT
  curl -s -X PUT -d "@@@AWS_ACCESS_KEY@@@" localhost:8500/v1/kv/socorro/webapp-django/AWS_ACCESS_KEY
  curl -s -X PUT -d "@@@AWS_SECRET_ACCESS_KEY@@@" localhost:8500/v1/kv/socorro/webapp-django/AWS_SECRET_ACCESS_KEY
  curl -s -X PUT -d "@@@SYMBOLS_BUCKET_DEFAULT_NAME@@@" localhost:8500/v1/kv/socorro/webapp-django/SYMBOLS_BUCKET_DEFAULT_NAME
  curl -s -X PUT -d "@@@SYMBOLS_BUCKET_EXCEPTIONS_USER@@@" localhost:8500/v1/kv/socorro/webapp-django/SYMBOLS_BUCKET_EXCEPTIONS_USER
  curl -s -X PUT -d "@@@SYMBOLS_BUCKET_EXCEPTIONS_BUCKET@@@" localhost:8500/v1/kv/socorro/webapp-django/SYMBOLS_BUCKET_EXCEPTIONS_BUCKET
  curl -s -X PUT -d "@@@SYMBOLS_BUCKET_DEFAULT_LOCATION@@@" localhost:8500/v1/kv/socorro/webapp-django/SYMBOLS_BUCKET_DEFAULT_LOCATION
  curl -s -X PUT -d "True" localhost:8500/v1/kv/socorro/webapp-django/ANALYZE_MODEL_FETCHES

Create partitioned tables
-------------------------

Normally this is handled automatically by the cronjob scheduler
:ref:`crontabber-chapter` but should be run as a one-off to create the PostgreSQL partitioned tables for processor
to write crashes to:
::
  cd /data/socorro
  ./socorro-virtualenv/bin/python application/socorro/cron/crontabber_app.py --job=weekly-reports-partitions --force


Start services
--------------

Both the Django socorro-webapp and the socorro-middleware REST service
must be running::

    sudo systemctl enable socorro-middleware socorro-webapp
    sudo systemctl start socorro-middleware socorro-webapp

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

Socorro uses a crontab manager called
`Crontabber <https://github.com/mozilla/crontabber>`_. This needs to be run from
system cron on a single host (generally referred to as the "admin host").

We suggest putting the following into /etc/cron.d/socorro::

    */5 * * * * socorro /data/socorro/application/scripts/crons/crontabber.sh

More documentation about Crontabber is `available here <https://crontabber.readthedocs.org/en/latest/>`_.

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
