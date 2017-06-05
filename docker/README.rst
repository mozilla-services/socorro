=========================
Docker environment README
=========================

Quickstart
==========

1. Install `Docker <https://docs.docker.com/engine/installation/>`_.

2. Install `docker-compose <https://docs.docker.com/compose/install/>`_. You need
   1.10 or higher.

   .. Note::

      It helps to add an alias to your shell::

        alias dc=docker-compose

      because it's way easier to type "dc" and I do it a log.

3. Install `make <https://www.gnu.org/software/make/>`_ using either your
   system's package manager (Linux) or homebrew (OSX) or FIXME (Windows).

4. From the root of this repository, run::

     $ make dockerbuild

   That will build the containers required for development: test, processor, and
   webapp.

5. Then you need to set up Postgres and Elasticssearch. To do that, run::

     $ make dockersetup

   .. Note::

      This is a work in progress, isn't idempotent, and is fussy about the state
      of things.

      Pull requests welcome!


At that point, you're good to go.


Configuration
=============

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


Running tests
=============

To run the tests, do::

  $ make dockertest


That runs the ``/app/docker/run_test.sh`` script in the webapp container using
test configuration.

To run specific things, you'll want to do it manually in a shell::

  $ docker-compose run test /bin/bash


Then do whatever parts of ``docker/run_test.sh`` you need to set up the
environment and you should be good to go.


Running the processor
=====================

To run the processor using the processor configuration, do::

  $ docker-compose up processor


That will bring up all the services the processor requires to run and start the
processor using the ``/app/docker/run_processor.sh`` script and the processor
configuration.

To ease debugging in the container, you can run a shell::

  $ docker-compose run processor /bin/bash


Then you can start and stop the processor and tweak files and all that jazz.

.. Note::

   The stackwalk binaries are in ``/stackwalk`` in the container.


Running the webapp
==================

To run the webapp using the webapp configuration, do::

  $ docker-compose up webapp


That will bring up all the services the webapp requires to run and start the
webapp using the ``/app/docker/run_webapp.sh`` script and the webapp
configuration.

To ease debugging in the container, you can run a shell::

  $ docker-compose run webapp /bin/bash


Then you can start and stop the webapp and tweak files and all that jazz.


.. Note::

   The ``STATIC_ROOT`` is set to ``/tmp/crashstats-static/`` rather than
   ``/app/webapp-django/static``. This nixes a ton of permissions-related
   problems because the process in the container runs as uid 10001 which is not
   the uid of the user you're using on your host computer.

   The problem this creates is that ``/tmp/crashstats-static/`` is ephemeral
   and any changes there disappear when you stop the container.

   If you want it persisted, you should mount that directory using ``volumes``
   in a ``docker-compose.override.yml`` file.

   https://docs.docker.com/compose/extends/
