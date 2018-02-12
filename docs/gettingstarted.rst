===============
Getting started
===============

This chapter covers getting started with Socorro using Docker for a local
development environment.

If you're interested in running Socorro in a server environment, then check out
:ref:`deploying-socorro-chapter`.


Quickstart
==========

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

2. Clone the repository so you have a copy on your host machine. Instructions
   are `on GitHub <https://github.com/mozilla-services/socorro>`_.

3. From the root of this repository, run::

     $ make dockerbuild

   That will build the Docker images required for development: processor,
   webapp, and crontabber.

   Each of these images covers a single Socorro component: processor, webapp,
   and crontabber.

4. Then you need to set up the Postgres database and Elasticssearch. To do that,
   run::

     $ make dockersetup

   This creates the Postgres database and sets up tables, stored procedures,
   integrity rules, types, and a bunch of other things. It also adds a bunch of
   static data to lookup tables.

   For Elasticsearch, it sets up Supersearch fields and the index for raw and
   processed crash data.

   You can run ``make dockersetup`` any time you want to wipe the Postgres
   database and Elasticsearch to pick up changes to those storage systems or
   reset your environment.

5. Then you need to pull in product release and some other data that makes
   Socorro go.

   To do that, run::

     $ make dockerupdatedata

   This adds data that changes day-to-day. Things like product builds and
   normalization data.

   Depending on what you're working on, you might want to run this weekly or
   maybe even daily.


At this point, you should have a basic functional Socorro development
environment that has no crash data in it.

If you need crash data, see :ref:`processor-chapter` for additional setup,
fetching crash data, and running the processor.

See :ref:`gettingstarted-chapter-updating` for how to maintain and update your
local development environment.

See :ref:`gettingstarted-chapter-configuration` for how configuration works and
about ``my.env``.

See :ref:`webapp-chapter` for additional setup and running the webapp.

See :ref:`crontabber-chapter` for additional setup and running crontabber.


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

  $ make dockerbuild


If there were changes to the database tables, stored procedures, types,
migrations, or anything like that, you'll need to wipe the Postgres database and
Elasticsearch::

  $ make dockersetup


After doing that, you'll definitely want to update data::

  $ make dockerupdatedata


Wiping the database
-------------------

Any time you want to wipe the database and start over, run::

  $ make dockersetup


Updating release data
---------------------

Release data and comes from running ftpscraper. After you run ftpscraper, you
have to run featured-versions-automatic which will update the featured versions
list. Additionally, there's other data that changes day-to-day that you need to
pick up in order for some views in the webapp to work well.

Updating that data is done with a single make rule.

Run::

  $ make dockerupdatedata


.. Note::

   This can take a long while to run and if you're running it against an
   existing database, then ftpscraper will "catch up" since the last time it ran
   which can take a long time, maybe hours.

   If you don't have anything in the database that you need, then it might be
   better to wipe the database and start over.


.. _gettingstarted-chapter-configuration:

Configuration
=============

All configuration is done with ENV files located in ``/app/docker/config/``.

``local_dev.env``
    This holds *secrets* and *environment-specific configuration* required
    to get services to work in a Docker-based local development environment.

    This should **NOT** be used for server environments, but you could base
    configuration for a server environment on this file.

``never_on_a_server.env``
    This holds a few environment variables that override secure defaults and are
    explicitly for a local development environment.

    **These should never show up in a server environment.**

``processor.env``, ``crontabber.env``, and ``webapp.env``
    These configuration files hold *behavioral configuration* for these three
    components for all environments--local development and servers.

    For example, if you want to add a new destination crash store to the system,
    you'd add it to ``processor.env``.

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


See the ``docker-compose.yml`` file for order of precedence and which EMV files
are used for which component container.


Setting configuration specific to your local dev environment
------------------------------------------------------------

There are some variables you need to set that are specific to your local dev
environment. Put them in ``my.env``.


Overriding configuration
------------------------

If you want to override configuration temporarily for your local development
environment, put it in ``my.env``.


General architecture
====================

.. graphviz::

   digraph G {
      rankdir=LR;

      client [shape=box3d, label="firefox"];

      subgraph antpig {
         rank=same;

         antenna [shape=rect, label="antenna"];
         pigeon [shape=cds, label="pigeon"];
      }

      subgraph stores {
         rank=same;

         postgres [shape=tab, label="Postgres", style=filled, fillcolor=gray];
         elasticsearch [shape=tab, label="Elasticsearch", style=filled, fillcolor=gray];
         telemetry [shape=tab, label="Telemetry (S3)", style=filled, fillcolor=gray];
      }

      subgraph stores2 {
         rabbitmq [shape=tab, label="RMQ", style=filled, fillcolor=gray];
         aws [shape=tab, label="S3", style=filled, fillcolor=gray];
      }

      subgraph processing {
         rank=same;

         processor [shape=rect, label="processor"];
         crontabber [shape=rect, label="crontabber"];
      }

      webapp [shape=rect, label="webapp"];

      client -> antenna [label="HTTP"];
      antenna -> aws [label="save raw"];

      aws -> pigeon [label="S3:PutObject"];
      pigeon -> rabbitmq [label="crash id for processing"];

      rabbitmq -> processor [label="crash id"];
      aws -> processor [label="load raw"];
      processor -> { aws, postgres, elasticsearch, telemetry } [label="save processed"];

      postgres -> webapp;
      aws -> webapp [label="load raw,processed"];
      elasticsearch -> webapp [label="search"];

      postgres -> crontabber;
      elasticsearch -> crontabber;

      { rank=min; client; }
   }


Arrows direction represents the flow of interesting information (crashes,
authentication assertions, cached values), not trivia like acks.

.. Warning::

   August 17th, 2017. Everything below this point needs to be updated.



Top-level folders
-----------------

If you clone our `git repository <https://github.com/mozilla/socorro>`_, you
will find the following folders. Here is what each of them contains:

+-----------------+-------------------------------------------------------------+
| Folder          | Description                                                 |
+=================+=============================================================+
| docker/         | Docker environment related scripts, configuration, and      |
|                 | other bits.                                                 |
+-----------------+-------------------------------------------------------------+
| docs/           | Documentation of the Socorro project (the one you are       |
|                 | reading right now).                                         |
+-----------------+-------------------------------------------------------------+
| scripts/        | Scripts for launching the different parts of the Socorro    |
|                 | application.                                                |
+-----------------+-------------------------------------------------------------+
| socorro/        | Core code of the Socorro project.                           |
+-----------------+-------------------------------------------------------------+
| sql/            | SQL scripts related to our PostgreSQL database. Contains    |
|                 | schemas and update queries.                                 |
+-----------------+-------------------------------------------------------------+
| tools/          | External tools used by Socorro.                             |
+-----------------+-------------------------------------------------------------+
| webapp-django/  | Front-end Django application (also called webapp). See      |
|                 | :ref:`webapp-chapter`.                                      |
+-----------------+-------------------------------------------------------------+


Socorro submodules
------------------

The core code module of Socorro, called ``socorro``, contains a lot of code.
Here are descriptions of every submodule in there:

+-------------------+---------------------------------------------------------------+
| Module            | Description                                                   |
+===================+===============================================================+
| cron              | All cron jobs running around Socorro.                         |
+-------------------+---------------------------------------------------------------+
| database          | PostgreSQL related code.                                      |
+-------------------+---------------------------------------------------------------+
| external          | Here are APIs related to external resources like databases.   |
+-------------------+---------------------------------------------------------------+
| processor         | Code for the processor component.                             |
+-------------------+---------------------------------------------------------------+
| submitter         | Code for the stage submitter component.                       |
+-------------------+---------------------------------------------------------------+
| unittest          | All our unit tests are here.                                  |
+-------------------+---------------------------------------------------------------+
| webapp            | Code for the webapp component.                                |
+-------------------+---------------------------------------------------------------+
