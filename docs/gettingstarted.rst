===============
Getting started
===============

This chapter covers getting started with Socorro using Docker for a local
development environment.

If you're interested in running Socorro in a server environment, then check out
:ref:`deploying-socorro-chapter`.


Quickstart
==========

1. Install `Docker <https://docs.docker.com/engine/installation/>`_.

2. Install `docker-compose <https://docs.docker.com/compose/install/>`_. You need
   1.10 or higher.

   .. Note::

      It helps to add an alias to your shell::

        alias dc=docker-compose

      because it's way easier to type "dc" and I do it a lot.

3. Install `make <https://www.gnu.org/software/make/>`_ using either your
   system's package manager (Linux) or homebrew (OSX).

   FIXME(willkg): Windows instructions?

4. From the root of this repository, run::

     $ make dockerbuild

   That will build the containers required for development: test, processor, and
   webapp.

5. Then you need to set up the Postgres database (tables, stored procedures,
   types, and such) and Elasticssearch. To do that, run::

     $ make dockersetup


   You can run ``make dockersetup`` any time you want to wipe the database, pick
   up changes in static data, stored procedures, types, migrations, etc.

   .. Warning::

      This is a work in progress and might be fussy about some things.

      Pull requests welcome!

6. Then you need to pull in product release and some other data that makes
   Socorro go.

   This data isn't static and it changes day to day, so depending on what you're
   working on, you might have to run this at the start of every day.

   To udpate data::

     $ make dockerupdatedata


At this point, you should have a basic functional Socorro development
environment.

See :ref:`gettingstarted-chapter-updating` for how to maintain and update your environment.

See :ref:`webapp-chapter` for additional setup and running the webapp.

See :ref:`processor-chapter` for additional setup and running the processor.


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


General architecture
====================

.. image:: block-diagram.png

Arrows direction represents the flow of interesting information (crashes,
authentication assertions, cached values), not trivia like acks.


Configuration
-------------

All configuration is done with ENV files located in ``/app/docker/config/``.

Each service uses ``docker_common.env`` and then a service-specific ENV file.

``docker_common.env``
    This holds secrets and environment-specific configuration required
    to get services to work in a docker environment for local development.

    This should NOT be used for server environments.

``test.env``
    This holds configuration specific to running the tests. It has some
    configuration value overrides because the tests are "interesting".

``processor.env`` and ``webapp.env``
    These configuration files hold behavioral configuration for these two things
    that work across ALL environments--local development and servers.

    For example, if you want to add a new destination crash store to the system,
    you'd add it to ``processor.env``.


In this way, we have behavioral configuration versioned alongside code changes
and we can more easily push and revert changes.


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
