.. _localdevenv-chapter:

===========================
Local dev environment setup
===========================

This chapter covers getting started with Socorro using Docker for a local
development environment.

.. contents::
   :local:

.. _setup-quickstart:

Setup Quickstart
================

1. Install required software: Docker, docker-compose (1.10+), make, and git.

   **Linux**:

       Use your package manager.

   **OSX**:

       Install `Docker for Mac <https://docs.docker.com/docker-for-mac/>`_ which
       will install Docker and docker-compose.

       Use `homebrew <https://brew.sh>`_ to install make and git::

         $ brew install make git

   **Other**:

       Install `Docker <https://docs.docker.com/engine/installation/>`_.

       Install `docker-compose <https://docs.docker.com/compose/install/>`_. You need
       1.10 or higher.

       Install `make <https://www.gnu.org/software/make/>`_.

       Install `git <https://git-scm.com/>`_.

2. Clone the repository so you have a copy on your host machine.

   Instructions for cloning are `on the Socorro page in GitHub
   <https://github.com/mozilla-services/socorro>`_.

3. (*Optional for Linux users*) Set UID and GID for Docker container user.

   If you're on Linux or you want to set the UID/GID of the app user that
   runs in the Docker containers, run::

     $ make my.env

   Then edit the file and set the ``SOCORRO_UID`` and ``SOCORRO_GID``
   variables. These will get used when creating the app user in the base
   image.

   If you ever want different values, change them in ``my.env`` and re-run
   ``make build``.

4. Build Docker images for Socorro services.

   From the root of this repository, run::

     $ make build

   That will build the app Docker image required for development.

5. Initialize Postgres, Elasticsearch, S3, and Pub/Sub.

   Then you need to set up services. To do that, run::

     $ make runservices

   This starts service containers. Then run::

     $ make setup

   This creates the Postgres database and sets up tables, stored procedures,
   integrity rules, types, and a bunch of other things. It also adds a bunch of
   static data to lookup tables.

   For Elasticsearch, it sets up Supersearch fields and the index for
   processed crash data.

   For S3, this creates the required buckets.

   For Pub/Sub, this creates topics and subscriptions.

6. Populate data stores with required data.

   Then you need to fetch product build data and normalization data that
   Socorro relies on that comes from external systems and changes day-to-day.

   To do that, run::

     $ make updatedata


At this point, you should have a basic functional Socorro development
environment that has no crash data in it.

.. Note::

   You can run ``make setup`` and ``make updatedata`` any time you want to
   throw out all state and re-initialize services.

.. Seealso::

   **Make changes to signature generation!**
       If you need to make changes to signature generation, see
       :ref:`signaturegeneration-chapter`.

   **Run the processor and get some crash data!**
       If you need crash data, see :ref:`processor-chapter` for additional
       setup, fetching crash data, and running the processor.

   **Update your local development environment!**
       See :ref:`gettingstarted-chapter-updating` for how to maintain and
       update your local development environment.

   **Learn about configuration!**
       See :ref:`gettingstarted-chapter-configuration` for how configuration
       works and about ``my.env``.

   **Run the webapp!**
       See :ref:`webapp-chapter` for additional setup and running the webapp.

   **Run scheduled tasks!**
       See :ref:`cron-chapter` for additional setup and running cronrun.


.. _gettingstarted-chapter-updating:

Updating data in a dev environment
==================================

Updating the code
-----------------

Any time you want to update the code in the repostory, run something like this from
the main branch::

  $ git pull


After you do that, you'll need to update other things.

If there were changes to the requirements files or setup scripts, you'll need to
build new images::

  $ make build


If there were changes to the database tables, stored procedures, types,
migrations, supersearch schema, or anything like that, you'll need to wipe
state and re-initialize services::

  $ make setup
  $ make updatedata


Wiping crash storage and state
------------------------------

Any time you want to wipe all the crash storage destinations, remove all the
data, and reset the state of the system, run::

  $ make setup
  $ make updatedata


Updating release data
---------------------

Release data and comes from running archivescraper. This is used by the
``BetaVersionRule`` in the processor.

Run::

  $ make updatedata


.. _gettingstarted-chapter-configuration:

Configuration
=============

Configuration is pulled from three sources:

1. Envronment variables
2. ENV files located in ``/app/docker/config/``. See ``docker-compose.yml`` for
   which ENV files are used in which containers, and their precedence.
3. Defaults for the processor are in ``socorro/processor/processor_app.py``
   in ``CONFIG_DEFAULTS``.

   Defaults for the webapp are in ``webapp-django/crashstats/settings/``.

The sources above are ordered by precedence, i.e. configuration values defined
by environment variables will override values from ENV files or defaults.

The following ENV files can be found in ``/app/docker/config/``:

``local_dev.env``
    This holds *secrets* and *environment-specific configuration* required
    to get services to work in a Docker-based local development environment.

    This should **NOT** be used for server environments, but you could base
    configuration for a server environment on this file.

``test.env``
    This holds configuration specific to running the tests. It has some
    configuration value overrides because the tests are "interesting".

This ENV file is found in the repository root:

``my.env``
    This file lets you override any environment variables set in other ENV files
    as well as set variables that are specific to your instance.

    It is your personal file for your specific development environment--it
    doesn't get checked into version control.

    The template for this is in ``docker/config/my.env.dist``.

In this way:

1. environmental configuration which covers secrets, hosts, ports, and
   infrastructure-specific things can be set up for every environment

2. behavioral configuration which covers how the code behaves and which classes
   it uses is versioned alongside the code making it easy to deploy and revert
   behavioral changes with the code depending on them

3. ``my.env`` lets you set configuration specific to your development
   environment as well as override any configuration and is not checked into
   version control


Setting configuration specific to your local dev environment
------------------------------------------------------------

There are some variables you need to set that are specific to your local dev
environment. Put them in ``my.env``.


Overriding configuration
------------------------

If you want to override configuration temporarily for your local development
environment, put it in ``my.env``.


Processing crashes
==================

Running the processor is pretty uninteresting since it'll just sit there until
you give it something to process.

In order to process something, you first need to acquire raw crash data, put the
data in the S3 container in the appropriate place, then you need to add the
crash id to the AWS SQS standard queue.

We have helper scripts for these steps.

All helper scripts run in the shell in the container::

    $ make shell

Some of the scripts require downloading production data from
`crash-stats.mozilla.org <https://crash-stats.mozilla.org>`_, and it is
useful to add an API token with higher permissions before entering the shell.


.. _`API token`:

Adding an API Token
-------------------

By default, the download scripts will fetch anonymized crash data, which does
not include personally identifiable information (PII). This anonymized data can
be used to test some workflows, but the the processor will not be able to
analyze memory dumps or generate signatures.

If you have access to memory dumps, you can fetch those with the crash data by
using an API token with these permissions:

* View Personal Identifiable Information
* View Raw Dumps

You can generate API tokens at `<https://crash-stats.mozilla.org/api/tokens/>`_.

.. Note::

   Make sure you treat any data you pull from production in accordance with our
   data policies that you agreed to when granted access to it.

Add the API token value to your ``my.env`` file::

    SOCORRO_API_TOKEN=apitokenhere

The API token is used by the download scripts (run inside ``$ make shell``),
but not directly by the processor.


scripts/process_crashes.sh
--------------------------

You can use the ``scripts/process_crashes.sh`` script which will fetch crash
data, sync it with the S3 bucket, and publish the crash ids to AWS SQS queue
for processing. If you have access to memory dumps and use a valid
`API token`_, then memory dumps will be fetched for processing as well.

It takes one or more crash ids as arguments.

For example:

.. code-block:: shell

   app@socorro:/app$ scripts/process_crashes.sh ed35821d-3af5-4fe9-bfa3-dc4dc0181128

You can also use it with ``fetch_crashids``:

.. code-block:: shell

   app@socorro:/app$ socorro-cmd fetch_crashids --num=1 | scripts/process_crashes.sh

After running ``scripts/process_crashes.sh``, you will need to run the
processor which will do the actual processing.

If you find this doesn't meet your needs, you can write a shell script using
the commands and scripts that ``process_crashes.sh`` uses. They are described
below.


socorro-cmd fetch_crashids
--------------------------

This will generate a list of crash ids from crash-stats.mozilla.org that meet
specified criteria. Crash ids are printed to stdout, so you can use this in
conjunction with other scripts or redirect to a file.

This pulls 100 crash ids from yesterday for Firefox product:

.. code-block:: shell

   app@socorro:/app$ socorro-cmd fetch_crashids

This pulls 5 crash ids from 2017-09-01:

.. code-block:: shell

   app@socorro:/app$ socorro-cmd fetch_crashids --num=5 --date=2017-09-01

This pulls 100 crash ids for criteria specified with a Super Search url that we
copy and pasted:

.. code-block:: shell

   app@socorro:/app$ socorro-cmd fetch_crashids "--url=https://crash-stats.mozilla.org/search/?product=Firefox&date=%3E%3D2017-09-05T15%3A09%3A00.000Z&date=%3C2017-09-12T15%3A09%3A00.000Z&_sort=-date&_facets=signature&_columns=date&_columns=signature&_columns=product&_columns=version&_columns=build_id&_columns=platform"

You can get command help:

.. code-block:: shell

   app@socorro:/app$ socorro-cmd fetch_crashids --help


socorro-cmd fetch_crash_data
----------------------------

This will fetch raw crash data from crash-stats.mozilla.org and save it in the
appropriate directory structure rooted at outputdir. If you have access to
memory dumps and use a valid `API token`_, then memory dumps will be fetched
for processing as well.

Usage from host:

.. code-block:: shell

   app@socorro:/app$ socorro-cmd fetch_crash_data <outputdir> <crashid> [<crashid> ...]


For example (assumes this crash exists):

.. code-block:: shell

   app@socorro:/app$ socorro-cmd fetch_crash_data ./testdata 5c9cecba-75dc-435f-b9d0-289a50170818


Use with ``fetch_crashids`` to fetch crash data from 100 crashes from yesterday
for Firefox:

.. code-block:: shell

   app@socorro:/app$ socorro-cmd fetch_crashids | socorro-cmd fetch_crash_data ./testdata


You can get command help:

.. code-block:: shell

   app@socorro:/app$ socorro-cmd fetch_crash_data --help


scripts/socorro_aws_s3.sh
-------------------------

This script is a convenience wrapper around the aws cli s3 subcommand that uses
Socorro environment variables to set the credentials and endpoint.

For example, this creates an S3 bucket named ``dev-bucket``:

.. code-block:: shell

   app@socorro:/app$ scripts/socorro_aws_s3.sh mb s3://dev-bucket/


This copies the contents of ``./testdata`` into the ``dev-bucket``:

.. code-block:: shell

   app@socorro:/app$ scripts/socorro_aws_s3.sh sync ./testdata s3://dev-bucket/


This lists the contents of the bucket:

.. code-block:: shell

   app@socorro:/app$ scripts/socorro_aws_s3.sh ls s3://dev-bucket/


Since this is just a wrapper, you can get help:

.. code-block:: shell

   app@socorro:/app$ scripts/socorro_aws_s3.sh help


socorro-cmd sqs
---------------

This script can manipulate the AWS SQS emulator and also publish crash ids
AWS SQS queues.

Typically, you'd use this to publish crash ids to the AWS SQS standard queue for
processing.

For example:

.. code-block:: shell

   app@socorro:/app$ socorro-cmd sqs publish local-dev-standard \
       ed35821d-3af5-4fe9-bfa3-dc4dc0181128


For help:

.. code-block:: shell

   app@socorro:/app$ socorro-cmd sqs publish --help


.. Note::

   Processing will fail unless the crash data is in the S3 container first!


Example using all the scripts
-----------------------------

Let's process crashes for Firefox from yesterday. We'd do this:

.. code-block:: shell

  # Set SOCORRO_API_TOKEN in my.env
  # Start bash in the socorro container
  $ make shell

  # Generate a file of crashids--one per line
  app@socorro:/app$ socorro-cmd fetch_crashids > crashids.txt

  # Pull raw crash data from -prod for each crash id and put it in the
  # "crashdata" directory on the host
  app@socorro:/app$ cat crashids.txt | socorro-cmd fetch_crash_data ./crashdata

  # Create a dev-bucket in localstack s3
  app@socorro:/app$ scripts/socorro_aws_s3.sh mb s3://dev-bucket/

  # Copy that data from the host into the localstack s3 container
  app@socorro:/app$ scripts/socorro_aws_s3.sh sync ./crashdata s3://dev-bucket/

  # Add all the crash ids to the queue
  app@socorro:/app$ cat crashids.txt | socorro-cmd sqs publish local-dev-standard

  # Then exit the container
  app@socorro:/app$ exit

  # Run the processor to process all those crashes
  $ docker-compose up processor


Processing crashes from the collector
=====================================

`Antenna <https://antenna.readthedocs.io/>`_ is the collector of the Socorro
crash ingestion pipeline. It was originally part of the Socorro repository, but
we extracted and rewrote it and now it lives in its own repository and
infrastructure.

Antenna deployments are based on images pushed to Docker Hub.

To run Antenna in the Socorro local dev environment, do::

  $ docker-compose up collector


It will listen on ``http://localhost:8888/`` for incoming crashes from a
breakpad crash reporter. It will save crash data to the ``dev-bucket`` in the
local S3 which is where the processor looks for it. It will publish the crash
ids to the AWS SQS standard queue.


Connect to PostgreSQL database
==============================

The local development environment's PostgreSQL database exposes itself on a
non-standard port when run with docker-compose. You can connect to it with the
client of your choice using the following connection settings:

* Username: ``postgres``
* Password: ``aPassword``
* Port: ``8574``

For example::

    PGPASSWORD=aPassword psql -h localhost -p 8574 -U postgres --no-password breakpad
