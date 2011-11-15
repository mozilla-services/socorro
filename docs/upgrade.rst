.. index:: upgrade

.. _upgrade-chapter:


=======
Upgrade
=======

Introduction
------------

With each release this page documents what changed that would break
your install. The most recent block is usually trunk and under
development.

Socorro 2.0
===========

Processor
---------

There is a new configuration parameter for Elastic Search called
'elasticSearchOoidSubmissionUrl'. In testing, the value was
"http://node14.generic.metrics.sjc1.mozilla.com:9999/queue/tasks/%s",
but the value in production will be different. However, the "%s" at
the end is required. Inquire with the Metrics team for the production
URL. It is likely that the hardware to support ES will not be in place
until 2011-06-29, so until Metrics can provide the proper URL, this
value should be the empty string "".

Middleware
----------

There are several new parameters in the middleware configuration file,
'webapiconfig.py.dist'. These new parameters support the use of
Elastic Search. In this deployment, Elastic Search will be disabled as
the search mechanism, so the value of the parameter,
'searchImplClass', should be overridden to be
'socorro.search.postgresAPI.PostgresAPI'.

Web App
-------

There is a key in webserviceclient.php-dist that is called
'middleware_implementation' that should be overridden to be "PG" as we
are using Postgres for this release.

PostgreSQL
----------

As usual, run 'scripts/upgrade/2.0/upgrade.sh'

This can be run either before or after the code deployment.

Socorro 1.7.8
=============

Postgres Database
-----------------

As usual, run scripts/upgrade/1.7.8/upgrade.sh.

This time, the upgrade script for Dev and for Prod are the same.

Note that pgbouncer_processor_pool.py can't really be run at
production time as it requires an interruption in service. It also
must be run as root. Therefore it's supplied by commented out. At
Mozilla, it has already been installed in prod.


Socorro 1.7.7
=============

Config
------

1. change to the builds config .dist file:

 cp scripts/config/buildsconfig.py.dist scripts/config/buildsconfig.py

2. change to the webapi config file:

 cp scripts/config/webapiconfig.py.dist scripts/config/webapiconfig.py

Web App
-------

**Config**

Edit application/config/config.php. Change the value of display errors
to TRUE. This will enable the new error page we have added.::

 $config['display_errors'] = TRUE;

**Cron**

Remove this line from the socorro crontab::

 05 01 * * * socorro /data/bin/cron_startdimproductdims.sh

Add these lines to the socorro crontab::

 02 * * * * socorro /data/socorro/application/scripts/crons/cron_duplicates.sh
 02 * * * * socorro /data/socorro/application/scripts/crons/cron_signatures.sh

Postgres Database
-----------------

**Config**

No changes for this version.

**Database Components**

**CITEXT**

We are now using the CITEXT, or "case insensitive text" data type. As
such, this will need to be loaded into the PostgreSQL database prior
to any of the database migration scripts.

1. On the MASTER database server, su to the "postgres" shell user.
2. psql -f /usr/pgsql-9.0/share/contrib/citext.sql breakpad

**plperl**

We are now using perl as a stored procedure language (in addition to
plpgsql). Before running any of the migrations, it needs to be loaded
into the database.

1. On the MASTER database server, su to the "postgres" shell user.
2. createlang plperl breakpad

Migration Scripts
-----------------

Unlike other upgrades, all SQL migration scripts for this upgrade are
checked into subversion. They are located at /scripts/upgrade/1.7.7/,
here:
http://code.google.com/p/socorro/source/browse/#svn%2Ftrunk%2Fscripts%2Fupgrade%2F1.7.7

Further, several of these migration scripts take minutes to hours to
run due to the need to backfill data. All are desinged to run without
taking down Socorro. As such, these migrations should be performed on
some schedule before the 1.7.7 code deployment.

The order they are given below is the order in which they should be
run. Currently these scripts are not in a state where the should be
run by someone without PostgreSQL experience; if that becomes
necessary, we will improve them.

**tk_version.sql**

Creates new tokenize_version function. Should run in seconds. Requires plperl.

**clean_up_versions.sql**

Fixes some longstanding data type issues with the productdims and
builds tables. Creates functions and dimension tables to make version
numbers sortable. Should run in less than a minute. Requires exclusive
locks on a few tables, so if it hangs, cancel and start over.

**first_report_migration.sql**

Creates and backfills several materialized view tables summarizing
"first appearance of signature" information. Will take a couple hours
to run.

As soon as this migration completes, the update_signature_matviews cron job should be enabled.

**find_dups.sql**

Creates tables and functions to support finding possible duplicate
reports. Should only take a couple minutes to run.

**backfill_dups.sql**

Creates functions to backfill lists of suspected duplicates. Will only
take a few seconds to run. After the functions are created, you will
need to run one of them in order to do the actually backfilling. This
is expected to take up to 8 hours.

1. record the current time/day. as an example, say it is currently '2011-03-07 15:30:00'
2. subtract 3 hours (example: '2011-03-07 12:30:00' )
3. run the following query: SELECT backfill_all_dups ( '2011-01-01', '2011-03-07 12:30:00' ). This will take 4-6 hours.
4. when it completes, backfill the gap: SELECT backfill_all_dups ( '2011-03-07 12:30:00', current_timestamp - interval '3 hours' );
5. when that completes, immediately enable the "find dups" cron job.

**new_reason_index.sql**

Adds an index on the "reason" column to all reports partitions. Will
take several hours to run.

This script has no dependancies on the others. As such, it could be
run either before or after them.

**postcrash_email.sql**

Adds a new status column to the email_campaigns and
email_campaigns_contacts tables, to support bug 630350.

Socorro 1.7.6
=============

There are numerous changes to the system for this release. For each of
the changes outlined below, it is assumed that the python codebase has
been updated to the latest 1.7.6 release. All the Python apps are
expecting to run under Python 2.4.

Throughout the system, rotating file logging has been eschewed for
syslogging instead. This change affects every nearly Python
configuration file in the system.

commonconfig.py
---------------

See :ref:`commonconfig-chapter` for details

Configuration file changes:

* any mention of the parameter crashStorageClass has been removed
* the entire NFS storage system section has been removed

Collector
---------

The :ref:`collector-chapter` can now use either the local file system as its
primary storage or submit directly to hbase. There are also mod-python
and mod-wsgi based collector versions.

The mod-python collector is found at
'.../socorro/collector/modpython-collector.py'. That file should be
copied to the mod-python directory and renamed 'collector.py'

More information and details on the configuration file can be found at
:ref:`collector-chapter`. Start by getting the
'.../scripts/config/commonconfig.py.dist' and
'.../scripts/config/collectorconfig.py.dist' and diff them with your
current configs. Make changes as necessary.

Configuration file changes:

* there are new parameters for local storage. If you're using local
  disk for primary crash storage use the values formerly used for
  fallback storage here.
* the fallbackFS should now be configured for an NFS mount or other
  local storage to be used in emergencies.
* the logger section no longer has the logFile parameters, they are
  replaced with syslog parameters.

Start your new collector and pass it some sample crashes. Tail your
syslog, grepping for 'Socorro Collector' to watch it work. You should
see it echo its configuration and then echo ooids as it accepts
crashes.

newCrashMover
-------------

This is a new app that replaces the hbaseResubmit.py from the previous
releases in this series.

For information regarding the configuration, see :ref:`crashmover-chapter`.

Monitor
-------

Configuration file changes:

* import of crashStorageClass from commonconfig has been removed
* the entire NFS storage system section has been removed
* the logger section no longer has the logFile parameters, they are
  replaced with syslog parameters.

Processor
---------

Configuration file changes:

* import of crashStorageClass from commonconfig has been removed
* the entire NFS storage system section has been removed
* the logger section no longer has the logFile parameters, they are
  replaced with syslog parameters.

Hoopsnake (the middleware)
--------------------------

Only a very minor change - just update the source and restart. There are no configuration changes.

Cron: createPartitions
----------------------

The only change to this application is the removal of the rotating
file logging and the addition of the syslogging. Update the
configuration from '.../scripts/config/createpartititonsconfig.py.dist'

Cron: startBugzilla
-------------------

The only change to this application is the removal of the rotating
file logging and the addition of the syslogging. Update the
configuration from '.../scripts/config/bugzillaconfig.py.dist'

Cron: startBuilds
-----------------

This app has been updated with new capabilities and has had changes to
its config file, as well as the builds table (see below). Update the
configuration from '.../scripts/config/startBuilds.py.dist'

Cron: startDailyCrash
---------------------

The only change to this application is the removal of the rotating
file logging and the addition of the syslogging. Update the
configuration from '.../scripts/config/dailycrashconfig.py.dist'

Cron: startDailyUrl
-------------------

The only change to this application is the removal of the rotating
file logging and the addition of the syslogging. Update the
configuration from '.../scripts/config/dailyurlconfig.py.dist'

Cron: startServerStatus
-----------------------

The only change to this application is the removal of the rotating
file logging and the addition of the syslogging. Update the
configuration from '.../scripts/config/serverstatusconfig.py.dist'

Cron: startTopCrashesByUrl
--------------------------

The only change to this application is the removal of the rotating
file logging and the addition of the syslogging. Update the
configuration from '.../scripts/config/TopCrashesByUrlConfig.py.dist'

Cron: startTopCrashesBySignature
--------------------------------

The only change to this application is the removal of the rotating
file logging and the addition of the syslogging. Update the
configuration from
'.../scripts/config/TopCrashesBySignatureConfig.py.dist'

Database
--------

**builds table**

Please run the following query, which will alter the builds table:
Note: The last 2 fields may have already been added in the 1.8 rollout::

 ALTER TABLE builds RENAME COLUMN changeset TO platform_changeset;
 ALTER TABLE builds ADD app_changeset_1 text;
 ALTER TABLE builds ADD app_changeset_2 text;

Web App
-------

**Config**

Add the following to application/config/application.php::

 /**
  * Base URL to which bugs will be submitted.
  */
 $config['report_bug_url'] = 'https://bugzilla.mozilla.org/enter_bug.cgi?';


Add the following to application/config/auth.php::

 /**
  * Setting to true will force every page on the site to use https; else set to false.
  */
 $config['force_https'] = true;

Add the following to application/config/products.php::

 /**
  * The number of topchangers to feature on the product dashboard.
  */
 $config['topchangers_count_dashboard'] = 15;

 /**
  * The number of topchangers to feature on the product dashboard.
  */
 $config['topchangers_count_page'] = 50;


Socorro 1.7.5
=============

Collector
---------

The collector has been reworked to do syslogging.

Configuration file changes:

* the logger section no longer has the logFile parameters, they are
  replaced with syslog parameters.

Processor
---------

The processor has changed to allow for jobs to be reprocessed. This
should resolve the stuck job problem. No configuration changes are
necessary.

Database
--------

The following database queries will set up the database for the new
email feature, 2 new cron jobs, shifting session storage from cookies
to the database, and updates to the top_crashes_by_signatures and
product_visibility tables.

Please note: some of the insert statements may execute in 2 to 3
minutes of time.::

 CREATE
     TABLE email_campaigns
     (
         id serial NOT NULL PRIMARY KEY,
         product TEXT NOT NULL,
         versions TEXT NOT NULL,
         signature TEXT NOT NULL,
         subject TEXT NOT NULL,
         body TEXT NOT NULL,
         start_date TIMESTAMP without TIME zone NOT NULL,
         end_date TIMESTAMP without TIME zone NOT NULL,
         email_count INTEGER DEFAULT 0,
         author TEXT NOT NULL,
         date_created TIMESTAMP without TIME zone NOT NULL DEFAULT now()
     );
 CREATE
     INDEX email_campaigns_product_signature_key ON email_campaigns
     (
         product,
         signature
     );
 CREATE
     TABLE email_contacts
     (
         id serial NOT NULL PRIMARY KEY,
         email TEXT NOT NULL,
         subscribe_token TEXT NOT NULL,
         subscribe_status BOOLEAN DEFAULT TRUE,
         CONSTRAINT email_contacts_email_unique UNIQUE (email),
         CONSTRAINT email_contacts_token_unique UNIQUE (subscribe_token)
     );
 CREATE
     TABLE email_campaigns_contacts
     (
         email_campaigns_id INTEGER REFERENCES email_campaigns (id),
         email_contacts_id INTEGER REFERENCES email_contacts (id),
         CONSTRAINT email_campaigns_contacts_mapping_unique UNIQUE (email_campaigns_id, email_contacts_id)
     );

 CREATE TABLE signature_productdims (
   signature text not null,
   productdims_id integer not null,
   UNIQUE (signature, productdims_id)
 );

 INSERT INTO signature_productdims
 SELECT
   tcbs.signature,
   tcbs.productdims_id
   FROM top_crashes_by_signature tcbs
 WHERE
   tcbs.window_end >= (NOW() - interval '4 weeks')
   AND tcbs.signature IS NOT NULL
 GROUP BY
   tcbs.signature,
   tcbs.productdims_id
 ;

 ALTER TABLE top_crashes_by_signature ADD COLUMN hang_count integer DEFAULT 0;

 ALTER TABLE top_crashes_by_signature ADD COLUMN plugin_count integer DEFAULT 0;

 ALTER TABLE product_visibility ADD throttle DECIMAL(5,2) DEFAULT 0.00;

 UPDATE product_visibility SET throttle = 10.00;
 UPDATE product_visibility SET throttle = 2.00 WHERE productdims_id = (SELECT id
 FROM productdims WHERE product = 'Firefox' AND version = '3.0.15');
 UPDATE product_visibility SET throttle = 2.00 WHERE productdims_id = (SELECT id
 FROM productdims WHERE product = 'Firefox' AND version = '3.0.16');
 UPDATE product_visibility SET throttle = 2.00 WHERE productdims_id = (SELECT id
 FROM productdims WHERE product = 'Firefox' AND version = '3.0.17');
 UPDATE product_visibility SET throttle = 2.00 WHERE productdims_id = (SELECT id
 FROM productdims WHERE product = 'Firefox' AND version = '3.0.18');
 UPDATE product_visibility SET throttle = 2.00 WHERE productdims_id = (SELECT id
 FROM productdims WHERE product = 'Firefox' AND version = '3.0.19');
 UPDATE product_visibility SET throttle = 2.00 WHERE productdims_id = (SELECT id
 FROM productdims WHERE product = 'Firefox' AND version = '3.0.20');
 UPDATE product_visibility SET throttle = 2.00 WHERE productdims_id = (SELECT id
 FROM productdims WHERE product = 'Firefox' AND version = '3.0.21');
 UPDATE product_visibility SET throttle = 2.00 WHERE productdims_id = (SELECT id
 FROM productdims WHERE product = 'Firefox' AND version = '3.5.5');
 UPDATE product_visibility SET throttle = 2.00 WHERE productdims_id = (SELECT id
 FROM productdims WHERE product = 'Firefox' AND version = '3.5.6');
 UPDATE product_visibility SET throttle = 2.00 WHERE productdims_id = (SELECT id
 FROM productdims WHERE product = 'Firefox' AND version = '3.5.7');
 UPDATE product_visibility SET throttle = 2.00 WHERE productdims_id = (SELECT id
 FROM productdims WHERE product = 'Firefox' AND version = '3.5.8');
 UPDATE product_visibility SET throttle = 2.00 WHERE productdims_id = (SELECT id
 FROM productdims WHERE product = 'Firefox' AND version = '3.5.9');

 CREATE TABLE sessions (
     session_id varchar(127) NOT NULL,
     last_activity integer NOT NULL,
     data text NOT NULL,
     CONSTRAINT session_id_pkey PRIMARY KEY (session_id),
     CONSTRAINT last_activity_check CHECK (last_activity >= 0)
 );

Cron
----

A new cron script has been added called SignatureProductdims?.

Enable 'scripts/startSignatureProductdims.py' to run nightly at
1:05am. Please run the script once to ensure that it works and logs
properly.

The following config file will need to be copied from the .dist file::

 cp scripts/config/signatureProductdims.py.dist scripts/config/signatureProductdims.py


Hoopsnake (the middleware)
--------------------------

The middleware has changes to support the new email feature as well as
syslogging.

Configuration file changes:

* Compare 'scripts/config/webapiconfig.py.dist' to
  'scripts/config/webapiconfig.py'
* the logger section no longer has the logFile parameters, they are
  replaced with syslog parameters.
* New config parameters::

    import socorro.services.emailCampaign as emailcampaign
    import socorro.services.emailCampaignCreate as emailcreate
    import socorro.services.emailCampaigns as emaillist
    import socorro.services.emailCampaignVolume as emailvolume
    import socorro.services.emailSubscription as emailsub

A secondary configuration file has been added called 'smtpconfig.py':
New Config file::

 cp smtpconfig.py.dist smtpconfig.py

Edit 'smtpconfig.py' with appropriate values for sending mail.

The unsubscribeBaseUrl should point to your webapp-php install.
Example::

 unsubscribeBaseUrl.default = "http://crash-stats.mozilla.com/email/subscription/%s"

Webapp
------

Add the config files for session.php and cookie.php::

 cp application/config/cookie.php-dist application/config/cookie.php
 cp application/config/session.php-dist application/config/session.php

ReCAPTCHA added.::

 cp webapp-php/modules/recaptcha/config/recaptcha.php-dist webapp-php/application/config/recaptcha.php

Edit recaptcha.php and add a valid domain, public, and private key
obtained from http://recaptcha.net

Edit 'webapp-php/application/config/config.php' and make sure
$config'modules'? has MODPATH . 'recaptcha',

Example::

 $config['modules'] = array
 (
     MODPATH . 'auth',
     MODPATH . 'ezcomponents',
     MODPATH . 'moz_pagination',
     MODPATH . 'recaptcha',
 );

Add the following config values to application/config/daily.php::

 /**
  * The default throttle rate for versions.
  */
 $config['throttle_default'] = '10.00';

Update the following config values in application/config/daily.php::

 $config['products'] = array('Firefox','Thunderbird', 'Camino', 'SeaMonkey', 'Fennec');

Scripts
-------

Run 'scripts/updateTopCrashesBySignature.py'. This will take a
significant amount of time to complete (greater than 1 hour). It is
used to backfill the hang_count and plugin_count values for each
signature over the last 4 weeks.


Socorro 1.7.4
=============

No configuration changes are required for this release.

Socorro 1.7
===========

This release retires all NFS storage in favor of HBase storage.

FINAL

The tagged code for 1.7 is at
http://socorro.googlecode.com/svn/tags/releases/1.7_r2148_20100610/

Outage page
-----------

[[Deployment]] has details on showing the 1.7 outage page to disable the web app.

New Database table
------------------

Execute::

 CREATE TABLE daily_crashes
     (
         id serial NOT NULL PRIMARY KEY,
         COUNT INTEGER DEFAULT 0 NOT NULL,
         report_type CHAR(1) NOT NULL DEFAULT 'C',
         productdims_id INTEGER REFERENCES productdims(id),
         os_short_name CHAR(3),
         adu_day TIMESTAMP WITHOUT TIME ZONE NOT NULL,
         CONSTRAINT day_product_os_report_type_unique UNIQUE (adu_day,
 productdims_id, os_short_name, report_type)
     )

Please give webserivces read access to daily_crashes

Please give cron jobs read/write access to daily_crashes

Config Files
------------

Extensive changes to the config files:

**commonconfig.py**

this file has been broken into sections. Use the
'.../scripts/config/commonconfig.py.dist' as a guide when upgrading to
the new format. The 'NFS storage system' section may be omitted since
we will not be using NFS. Use the same connection information that was
used in the 1.6.X collector config for the HBase config parameters.

`Diff comparing commonconfig.py.dist v1.7 with previous versions
<http://code.google.com/p/socorro/source/diff?spec=svn2141&old=1559&r=2122&format=side&path=%2Ftrunk%2Fscripts%2Fconfig%2Fcommonconfig.py.dist>`_

**collectorconfig.py**

this file has been broken into sections. Use
'.../scripts/config/collectorconfig.py.dist' as a guide to the
rearrangement.

* a new import of the parameter 'crashStorageClass' has been added
* a HBase section has been added
   * HBase now has its own values for permissions, GUID and DumpDirCount?
   * a new parameter called 'useBackupNFSStorage' has been added.
   * the HBase section has a place for NFS backup file system
     parameters. These are required only if 'useBackupNFSStorage' has
     been set to True.
* an NFS section has been added (may be disregarded) This is only for
  use if NFS is to be the primary crash storage mechanism

`Diff comparing collectorconfig.py.dist v1.7 with previous
versions
<http://code.google.com/p/socorro/source/diff?spec=svn2141&old=1559&r=2122&format=side&path=%2Ftrunk%2Fscripts%2Fconfig%2Fcollectorconfig.py.dist>`_

**processorconfig.py**

Use '.../scripts/config/processor.py.dist' as a guide. Several options
have changed position within the file for better organization. It may
be best to start with the .dist' file and use the existing config file
as a guide to create a new one.

* the "import star" has been replaced with a section called imported config
* a new import of the parameter 'crashStorageClass' has been added
* an HBase section has been added
* an NFS section has been added (may be disregarded)
* a new parameter in the HBase section is called
  'temporaryFileSystemStoragePath'. This value is to be local
  filesystem path for the temporary storage of dump files. In the hbase
  system, the dump files are not stored in a file that
  minidump_stactwalk can read. This path will hold temporary dump files.
  The directory should be self cleaning, no old dumps should accumulate
  there.
* a future use parameter has been added to the Processor Local Config
  section called "updateInterval". It may be disregarded for this
  update

`Diff comparing processorconfig.py.dist' v1.7 with previous
versions
<http://code.google.com/p/socorro/source/diff?spec=svn2141&old=1559&r=2122&format=side&path=%2Ftrunk%2Fscripts%2Fconfig%2Fprocessorconfig.py.dist>`_

**monitorconfig.py**

Please follow '.../scripts/config/monitorconfig.py.dist' as a guide.
Several options have changed position within the file for better
organization. It may be best to start with the .dist' file and use the
existing config file as a guide to create a new one.

* the "import star" has been replaced with a section called "imported config"
* a new import of the parameter 'crashStorageClass' has been added
* an HBase section has been added
* an NFS section has been added (may be disregarded)
* a local monitor config section has been added

`Diff comparing monitorconfig.py.dist' v1.7 with previous
versions
<http://code.google.com/p/socorro/source/diff?spec=svn2141&old=1559&r=2122&format=side&path=%2Ftrunk%2Fscripts%2Fconfig%2Fmonitorconfig.py.dist>`_

**webapiconfig.py**

a new service has been added called GetCrash?. Use
'.../scripts/config/webapiconfig.py as a guide. The changes include:

* additional import of 'crashStorageClass'
* addition of the HBase section
* addition of NFS section (may be disregarded)
* import of socorro.services.getCrash
* addition of "crash.GetCrash?" to the servicesList
* addition of "adubd.AduByDay200912?" to the serviceList

`Diff comparing webapiconfig.py.dist' v1.7 with previous
versions
<http://code.google.com/p/socorro/source/diff?spec=svn2141&old=1559&r=2122&format=side&path=%2Ftrunk%2Fscripts%2Fconfig%2Fwebapiconfig.py.dist>`_

**hbaseresubmitconfig.py**

Use '.../scripts/config/hbaseresubmitconfig.py.dist' as a guide. The
changes include:

* the import location for the parameter, 'hbaseHost' has changed to commonconfig.py
* the import location for the parameter, 'hbasePort' has changed to commonconfig.py
* addition of a the new parameter 'hbaseTimeout'

`Diff comparing hbaseresubmitconfig.py.dist' v1.7 with previous
versions
<http://code.google.com/p/socorro/source/diff?spec=svn2145&old=1559&r=2145&format=side&path=%2Ftrunk%2Fscripts%2Fconfig%2Fhbaseresubmitconfig.py.dist>`_

**config/dailycrashconfig.py**

Copy 'config/dailycrashconfig.py.dist' to 'config/dailycrashconfig.py'


Scripts & Library
-----------------

there have been extensive changes to the codebase of Socorro

**new Daily Crash Cron**

1. Run scripts/startDailyCrash.py

Make sure you have the same env as a cron job (PYTHONPATH, etc) and wait for it to complete before installing as a cron. DB permissions should have been granted in previous steps.

2. install as a daily cron that starts at 00:15am once per day

**Collector**

* stop collector
* update to the latest version of the Socorro library
* update to the latest version of the thirdparty library
* update config as instructed above
* restart collectors

**Processor**

* stop monitor, processors
* update to the latest version of the Socorro library
* update to the latest version of the thirdparty library
* the script that starts the processor has changed, update '.../scripts/startProcessor.py
* update config as instructed above
* restart processors

**Monitor**

* update to the latest version of the Socorro library
* update to the latest version of the thirdparty library
* update config as instructed above
* restart monitor

**Web Services**

* stop the mod-wsgi web service
* update to the latest version of the Socorro library
* update to the latest version of the thirdparty library
* update config as instructed above
* restart the web service
* test daily_crashes table by running (change hostname and port as
  needed)::

    curl "http://localhost:8085/201005/adu/byday/p/Firefox/v/3.6.4/rt/any/os/Windows;Mac;Linux/start/2010-05-22/end/2010-06-10"

attach results to deployment bug

Related info: https://bugzilla.mozilla.org/show_bug.cgi?id=567923
staging bug for daily_crashes ADU daily code.

HBase upgrade
-------------

1. Download http://people.apache.org/~stack/hbase-0.20.5-20100602.tar.gz to admin node
2. Extract package to /usr/lib
3. Symlink to /usr/lib/hbase-0.20.5
4. Copy Cloudera CDH 2 Hadoop jars from /usr/lib/hadoop to /usr/lib/hbase-0.20.5/lib
5. Copy LZH files (hadoop-gpl-compression.jar; native/Linux-amd64-64/libgplcompression) from /usr/lib/hbase/lib to /usr/lib/hbase-0.20.5/lib
6. Symlink hbase logs directory to /usr/lib/hbase-0.20.5/logs
7. (TODO: document config changes)
8. Copy over new HBase config files to /usr/lib/hbase-0.20.5/conf
9. rsync /usr/lib/hbase-0.20.5-20100602 to all machines
10. Symlink to /usr/lib/hbase-0.20.5 on all machines
11. on worker nodes: /etc/init.d/hbase-0.20-thrift stop
12. on master: sudo -u hadoop /usr/lib/hbase/bin/stop-hbase.sh
13. Symlink /usr/lib/hbase-0.20.5 to /usr/lib/hbase
14. on master: sudo -u hadoop /usr/lib/hbase/bin/start-hbase.sh
15. hbase org.jruby.Main set_meta_block_caching.rb
16. Make schema changes (TODO link to schema file)
17. on worker nodes: /etc/init.d/hbase-0.20-thrift start

WebUI upgrade
-------------

1. Update the webapp code to the latest tag
2. Purge caches

**config/application.php**

Add the following lines to the application.php config file::

 /**
  * The query range limit for users who have the role of user and admin.
  *
  * @see My_SearchReportHelper->normalizeDateUnitAndValue()
  */
 $config['query_range_defaults'] = array(
     'admin' => array(
         'range_default_value' => 14,
         'range_default_unit' => 'days',
         'range_limit_value_in_days' => 120
     ),
     'user' => array(
         'range_default_value' => 14,
         'range_default_unit' => 'days',
         'range_limit_value_in_days' => 30
     )
 );
