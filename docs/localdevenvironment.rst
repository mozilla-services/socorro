.. _localdevenv-chapter:

===========================
Local dev environment setup
===========================

This chapter covers getting started with Socorro using Docker for a local
development environment.

If you're interested in running Socorro in a server environment, then check out
:ref:`deploying-socorro-chapter`.

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

3. (*Optional/Advanced*) Set UID and GID for Docker container user.

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

   That will build the Docker images required for development: processor,
   webapp, and crontabber.

   Each of these images covers a single Socorro component: processor, webapp,
   and crontabber.

5. Initialize Postgres, Elasticsearch, S3, and Pub/Sub.

   Then you need to set up services. To do that, run::

     $ make runservices

   This starts services containers. Then run::

     $ make setup

   This creates the Postgres database and sets up tables, stored procedures,
   integrity rules, types, and a bunch of other things. It also adds a bunch of
   static data to lookup tables.

   For Elasticsearch, it sets up Supersearch fields and the index for raw and
   processed crash data.

   For S3, this creates the required buckets.

   For Pub/Sub, this creates topics and subscriptions.

   You can run ``make setup`` any time you want to re-initialize those
   services and wipe any data.

6. Populate data stores with required data.

   Then you need to pull in product release and some other data that makes
   Socorro go.

   To do that, run::

     $ make updatedata

   This adds data that changes day-to-day. Things like product builds and
   normalization data.

   Depending on what you're working on, you might want to run this weekly or
   maybe even daily.


At this point, you should have a basic functional Socorro development
environment that has no crash data in it.

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

   **Run crontabber!**
       See :ref:`crontabber-chapter` for additional setup and running
       crontabber.


.. _gettingstarted-chapter-updating:

Updating data in a dev environment
==================================

Updating the code
-----------------

Any time you want to update the code in the repostory, run something like this from
the master branch::

  $ git pull


It depends on what you're working on and the state of things.

After you do that, you'll need to update other things.

If there were changes to the requirements files or setup scripts, you'll need to
build new images::

  $ make build


If there were changes to the database tables, stored procedures, types,
migrations, or anything like that, you'll need to wipe the Postgres database and
Elasticsearch::

  $ make setup


After doing that, you'll definitely want to update data::

  $ make updatedata


Wiping crash storage and state
------------------------------

Any time you want to wipe all the crash storage destinations, remove all the
data, and reset the state of the system, run::

  $ make setup


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
3. Defaults for crontabber are in ``socorro/cron/crontabber_app.py`` in
   ``CronTabberApp.config_defaults``.

   Defaults for the processor are in ``socorro/processor/processor_app.py``
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

``never_on_a_server.env``
    This holds a few environment variables that override secure defaults and are
    explicitly for a local development environment.

    **These should never show up in a server environment.**

``test.env``
    This holds configuration specific to running the tests. It has some
    configuration value overrides because the tests are "interesting".

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
