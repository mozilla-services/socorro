.. _localdevenv-chapter:

===========
Development
===========

This chapter covers getting started with Socorro using Docker for a local
development environment.

.. contents::
   :local:

.. _setup-quickstart:

Setup quickstart
================

1. Install required software: Docker, make, and git.

   **Linux**:

       Use your package manager.

   **OSX**:

       Install `Docker for Mac <https://docs.docker.com/docker-for-mac/>`_ which
       will install Docker.

       Use `homebrew <https://brew.sh>`_ to install make and git:

       .. code-block:: shell

          $ brew install make git

   **Other**:

       Install `Docker <https://docs.docker.com/engine/installation/>`_.

       Install `make <https://www.gnu.org/software/make/>`_.

       Install `git <https://git-scm.com/>`_.

2. Clone the repository so you have a copy on your host machine.

   Instructions for cloning are `on the Socorro page in GitHub
   <https://github.com/mozilla-services/socorro>`_.

3. (*Optional for Linux users*) Set UID and GID for Docker container user.

   If you're on Linux or you want to set the UID/GID of the app user that
   runs in the Docker containers, run:

   .. code-block:: shell

      $ make my.env

   Then edit the file and set the ``SOCORRO_UID`` and ``SOCORRO_GID``
   variables. These will get used when creating the app user in the base
   image.

   If you ever want different values, change them in ``my.env`` and re-run
   ``make build``.

4. Build Docker images for Socorro services.

   From the root of this repository, run:

   .. code-block:: shell

      $ make build

   That will build the app Docker image required for development.

5. Initialize Postgres, Elasticsearch, S3, and SQS.

   Then you need to set up services. To do that, run:

   .. code-block:: shell

      $ make runservices

   This starts service containers. Then run:

   .. code-block:: shell

      $ make setup

   This creates the Postgres database and sets up tables, stored procedures,
   integrity rules, types, and a bunch of other things. It also adds a bunch of
   static data to lookup tables.

   For Elasticsearch, it sets up Super Search fields and the index for
   processed crash data.

   For S3, this creates the required buckets.

   For SQS, this creates queues.

6. Populate data stores with required data.

   Then you need to fetch product build data and normalization data that
   Socorro relies on that comes from external systems and changes day-to-day.

   To do that, run:

   .. code-block:: shell

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


Bugs / Issues
=============

We use `Bugzilla <https://bugzilla.mozilla.org/>`_ for bug tracking.

`Existing bugs <https://bugzilla.mozilla.org/buglist.cgi?quicksearch=product%3Asocorro>`_

`Write up a new bug <https://bugzilla.mozilla.org/enter_bug.cgi?product=Socorro&component=General>`_

If you want to do work for which there is no bug, please write up a bug first
so we can work out the problem and how to approach a solution.


Code workflow
=============

Bugs
----

Either write up a bug or find a bug to work on.

Assign the bug to yourself.

Work out any questions about the problem, the approach to fix it, and any
additional details by posting comments in the bug.


Pull requests
-------------

Pull request summary should indicate the bug the pull request addresses. Use a hyphen between "bug" and the bug ID(s). For
example::

    bug-nnnnnnn: removed frog from tree class

For multiple bugs fixed within a single pull request, list the bugs out individually. For example::
   
   bug-nnnnnnn, bug-nnnnnnn: removed frog from tree class

Pull request descriptions should cover at least some of the following:

1. what is the issue the pull request is addressing?
2. why does this pull request fix the issue?
3. how should a reviewer review the pull request?
4. what did you do to test the changes?
5. any steps-to-reproduce for the reviewer to use to test the changes

After creating a pull request, attach the pull request to the relevant bugs.

We use the `rob-bugson Firefox addon
<https://addons.mozilla.org/en-US/firefox/addon/rob-bugson/>`_. If the pull
request has "bug-nnnnnnn: ..." or "bug-nnnnnnn, bug-nnnnnnn: ..." in the summary, then rob-bugson will see that
and create a "Attach this PR to bug ..." link.

Then ask someone to review the pull request. If you don't know who to ask, look
at other pull requests to see who's currently reviewing things.


Code reviews
------------

Pull requests should be reviewed before merging.

Style nits should be covered by linting as much as possible.

Code reviews should review the changes in the context of the rest of the system.


Landing code
------------

Once the code has been reviewed and all tasks in CI pass, the pull request
author should merge the code.

This makes it easier for the author to coordinate landing the changes with
other things that need to happen like landing changes in another repository,
data migrations, configuration changes, and so on.

We use "Rebase and merge" in GitHub.


Conventions
===========

For conventions, see:
`<https://github.com/mozilla-services/socorro/blob/main/.editorconfig>`_


Python code conventions
-----------------------

All Python code files should have an MPL v2 header at the top::

  # This Source Code Form is subject to the terms of the Mozilla Public
  # License, v. 2.0. If a copy of the MPL was not distributed with this
  # file, You can obtain one at http://mozilla.org/MPL/2.0/.


To lint the code:

.. code-block:: shell

   $ make lint

If you hit issues, use ``# noqa``.

To run the reformatter:

.. code-block:: shell

   $ make lintfix

We're using:

* `black <https://black.readthedocs.io/en/stable/>`_:  code formatting
* `ruff <https://beta.ruff.rs/docs/>`_: linting


HTML conventions
----------------

2-space indentation.


Javascript code conventions
---------------------------

2-space indentation.

We're using:

* `eslint <https://eslint.org/>`_: linting


Git conventions
---------------

First line is a summary of the commit. It should start with the bug number. Use a hyphen between "bug" and the bug ID(s). For example::

   bug-nnnnnnn: summary

For multiple bugs fixed within a single commit, list the bugs out individually. For example::

   bug-nnnnnnn, bug-nnnnnnn: summary

After that, the commit should explain *why* the changes are being made and any
notes that future readers should know for context.


Migrations
==========

Database migrations (Django)
----------------------------

We use Django's ORM and thus we do database migrations using Django's
migration system.

Do this:

.. code-block:: shell

   $ make shell
   app@socorro:/app$ cd webapp
   app@socorro:/app/webapp$ ./manage.py makemigration --name "BUGID_desc" APP


Elasticsearch migrations (Elasticsearch)
----------------------------------------

We don't do migrations of Elasticsearch data. The system creates a new index
every week, so any changes to new fields or mappings will be reflected the
next time it creates an index.


Dependencies
============

Python Dependencies
-------------------

Python dependencies for all parts of Socorro are in ``requirements.in``
and compiled using ``pip-compile`` with hashes and dependencies of dependencies
in the ``requirements.txt`` file.

For example, to add ``foobar`` version 5:

1. add ``foobar==5`` to ``requirements.in``
2. run:

   .. code-block:: shell

      $ make rebuildreqs

   to apply the updates to ``requirements.txt``

3. rebuild your docker environment:

   .. code-block:: shell

      $ make build

If there are problems, it'll tell you.

In some cases, you might want to update the primary and all the secondary
dependencies. To do this, run:

.. code-block:: shell

   $ make updatereqs


JavaScript Dependencies
-----------------------

Frontend dependencies for the webapp are in ``webapp/package.json``. They
must be pinned and included in
`package-lock.json <https://docs.npmjs.com/files/package-locks>`_.

You can add new dependencies using ``npm`` (you must use version 5 or higher):

.. code-block:: shell

   $ npm install --save-exact foobar@1.0.0

Then rebuild your docker environment:

.. code-block:: shell

   $ make build

If there are problems, it'll tell you.


Documentation
=============

Documentation for Socorro is build with `Sphinx
<http://www.sphinx-doc.org/en/stable/>`_ and is available on ReadTheDocs. API is
automatically extracted from docstrings in the code.

To build the docs, run this:

.. code-block:: shell

   $ make docs


Testing
=======

Running tests
-------------

The Socorro tests are in ``socorro/tests/``.

The webapp tests are in ``webapp/``.

Both sets of tests use `pytest <https://pytest.org/>`_.

To run the tests, do:

.. code-block:: shell

   $ make test

That runs the ``/app/bin/test.sh`` script in the test container using test
configuration.

To run specific tests or specify arguments, you'll want to start a shell in the
test container:

.. code-block:: shell

   $ make testshell

Then you can run pytest on the Socorro tests or the webapp tests.

Running the Socorro tests:

.. code-block:: shell

   app@socorro:/app$ pytest

Running the webapp tests (make sure you run ``./manage.py collectstatic`` first):

.. code-block:: shell

   app@socorro:/app$ cd webapp
   app@socorro:/app/webapp$ ./manage.py collectstatic
   app@socorro:/app/webapp$ ./manage.py test

.. Note::

   For the webapp tests, you have to run ``./manage.py collectstatic`` before
   running the tests.


Writing tests
-------------

For Socorro tests, put them in ``socorro/tests/`` in a subdirectory parallel
to the thing you're testing.

For webapp tests, put them in the ``tests/`` directory of the appropriate app in
``webapp/`` directory tree.


Repository structure
====================

If you clone our `git repository
<https://github.com/mozilla-services/socorro>`_, you will find the following
folders.

Here is what each of them contains:

**bin/**
    Scripts for building Docker images, running Docker containers, deploying,
    and supporting development in a local development environment.

**docker/**
    Docker environment related scripts, configuration, and other bits.

**docs/**
    Documentation of the Socorro project (you're reading it right now).

**socorro/**
    The bulk of the Socorro source code.

**webapp/**
    The webapp source code.


.. _gettingstarted-chapter-updating:

Updating data in a dev environment
==================================

Updating the code
-----------------

Any time you want to update the code in the repostory, run something like this from
the main branch:

.. code-block:: shell

   $ git pull


After you do that, you'll need to update other things.

If there were changes to the requirements files or setup scripts, you'll need to
build new images:

.. code-block:: shell

   $ make build


If there were changes to the database tables, stored procedures, types,
migrations, Super Search schema, or anything like that, you'll need to wipe
state and re-initialize services:

.. code-block:: shell

   $ make setup
   $ make updatedata


Wiping crash storage and state
------------------------------

Any time you want to wipe all the crash storage destinations, remove all the
data, and reset the state of the system, run:

.. code-block:: shell

   $ make setup
   $ make updatedata


Updating release data
---------------------

Release data and comes from running archivescraper. This is used by the
``BetaVersionRule`` in the processor.

Run:

.. code-block:: shell

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

   Defaults for the webapp are in ``webapp/crashstats/settings/``.

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

All helper scripts run in the shell in the container:

.. code-block::

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


bin/process_crashes.sh
----------------------

You can use the ``bin/process_crashes.sh`` script which will fetch crash
data, sync it with the S3 bucket, and publish the crash ids to AWS SQS queue
for processing. If you have access to memory dumps and use a valid
`API token`_, then memory dumps will be fetched for processing as well.

It takes one or more crash ids as arguments.

For example:

.. code-block:: shell

   app@socorro:/app$ bin/process_crashes.sh ed35821d-3af5-4fe9-bfa3-dc4dc0181128

You can also use it with ``fetch_crashids``:

.. code-block:: shell

   app@socorro:/app$ socorro-cmd fetch_crashids --num=1 | bin/process_crashes.sh

After running ``bin/process_crashes.sh``, you will need to run the
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


bin/socorro_aws_s3.sh
---------------------

This script is a convenience wrapper around the aws cli s3 subcommand that uses
Socorro environment variables to set the credentials and endpoint.

For example, this creates an S3 bucket named ``dev-bucket``:

.. code-block:: shell

   app@socorro:/app$ bin/socorro_aws_s3.sh mb s3://dev-bucket/


This copies the contents of ``./testdata`` into the ``dev-bucket``:

.. code-block:: shell

   app@socorro:/app$ bin/socorro_aws_s3.sh sync ./testdata s3://dev-bucket/


This lists the contents of the bucket:

.. code-block:: shell

   app@socorro:/app$ bin/socorro_aws_s3.sh ls s3://dev-bucket/


Since this is just a wrapper, you can get help:

.. code-block:: shell

   app@socorro:/app$ bin/socorro_aws_s3.sh help


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
  app@socorro:/app$ bin/socorro_aws_s3.sh mb s3://dev-bucket/

  # Copy that data from the host into the localstack s3 container
  app@socorro:/app$ bin/socorro_aws_s3.sh sync ./crashdata s3://dev-bucket/

  # Add all the crash ids to the queue
  app@socorro:/app$ cat crashids.txt | socorro-cmd sqs publish local-dev-standard

  # Then exit the container
  app@socorro:/app$ exit

  # Run the processor to process all those crashes
  $ docker compose up processor


Processing crashes from the collector
=====================================

`Antenna <https://antenna.readthedocs.io/>`_ is the collector of the Socorro
crash ingestion pipeline. It was originally part of the Socorro repository, but
we extracted and rewrote it and now it lives in its own repository and
infrastructure.

Antenna deployments are based on images pushed to Docker Hub.

To run Antenna in the Socorro local dev environment, do::

  $ docker compose up collector


It will listen on ``http://localhost:8888/`` for incoming crashes from a
breakpad crash reporter. It will save crash data to the ``dev-bucket`` in the
local S3 which is where the processor looks for it. It will publish the crash
ids to the AWS SQS standard queue.


Connect to PostgreSQL database
==============================

The local development environment's PostgreSQL database exposes itself on a
non-standard port when run with docker compose. You can connect to it with the
client of your choice using the following connection settings:

* Username: ``postgres``
* Password: ``postgres``
* Port: ``8574``
* Database: ``socorro``

For example::

    PGPASSWORD=postgres psql -h localhost -p 8574 -U postgres --no-password socorro

You can also connect with ``make``::

    make psql
