.. _webapp-chapter:

==================
Crash Stats Webapp
==================

Code is in ``webapp/``.

Run script is ``/app/bin/run_webapp.sh``.


Configuration
=============

FIXME


Running in a local dev environment
==================================

To run the webapp, do::

  $ docker compose up webapp

To ease debugging, you can run a shell in the container::

  $ docker compose run --service-ports webapp shell

Then you can start and stop the webapp, adjust files, and debug.

If you want to do anything in the webapp admin, you'll need to create a
superuser in the Crash Stats webapp and a OIDC account to authenticate against
in the oidcprovider service container.

Let's use these credentials:

* username: willkg
* password: foo
* email: willkg@example.com

This creates an account in the oidcprovider service container::

  $ docker compose up -d oidcprovider
  $ docker compose exec oidcprovider /code/manage.py createuser willkg foo willkg@example.com

This creates a superuser account in the Crash Stats webapp corresponding to the
account we created in the oidcprovider service container::

  $ docker compose run app shell ./webapp/manage.py makesuperuser willkg@example.com

Feel free to use different credentials.

.. Note::

   You will have to recreate both of these accounts any time you do something
   that recreates the postgres db or restarts the oidcprovider service
   container.

   Best to put account creationg in a shell script so you can recreate both
   accounts easily.


Permissions
===========

The webapp uses Django's
`groups and permissions <https://docs.djangoproject.com/en/2.2/topics/auth/>`_
to define access groups for sensitive data such as Personally Identifiable
Information (PII). There are three main classes of users:

* Anonymous visitors and basic users do not have access to memory dumps or PII.
* Users in the "Hackers" group can view memory dumps and PII.
  `Memory Dump Access <https://crash-stats.mozilla.org/documentation/memory_dump_access/>`_
  has the details for requesting access to this group.
* Superusers maintain the site, set group membership in the Django admin, and
  have full access.

A logged-in user can view their detailed permissions on the
`Your Permissions <https://crash-stats.mozilla.org/permissions/>`_ page.

The groups and their permissions are defined in
``webapp/crashstats/crashstats/signals.py``. These are applied to
the database in a "post-migrate" signal handler.


Static Assets
=============

In the development environment, the ``STATIC_ROOT`` is set to
``/tmp/crashstats-static/`` rather than ``/app/webapp/static``.
The process in the container creates files with the uid 10001, and Linux users
will have permissions-related problems if these are mounted on the host
computer.

The problem this creates is that ``/tmp/crashstats-static/`` is ephemeral
and any changes there disappear when you stop the container.

If you are on macOS or Windows, then Docker uses a shared file system that
creates files with your user ID. This makes it safe to persist static assets,
at the cost of slower file system performance. Linux users can manually set
the uid and gid to match their account, for the same effect. See "Set UID and
GID for Docker container user" in :ref:`setup-quickstart`.

If you want static assets to persist between container restarts, then you
can override ``STATIC_ROOT`` in ``my.env`` to return it to the ``app`` folder::

    STATIC_ROOT=/app/static

Alternatively, you can mount ``/tmp/crashstats-static/`` using ``volumes``
in a ``docker compose.override.yml`` file:

.. code-block:: yaml

    version: "2"
    services:
      webapp:
        volumes:
          # Persist the static files folder
          - ./static:/tmp/crashstats-static


Production-style Assets
=======================

When you run ``docker compose up webapp`` in the local development environment,
it starts the web app using Django's ``runserver`` command. ``DEBUG=True`` is
set in the ``docker/config/local_dev.env`` file, so static assets are
automatically served from within the individual Django apps rather than serving
the minified and concatenated static assets you'd get in a production-like
environment.

If you want to run the web app in a more "prod-like manner", you want to run the
webapp using ``gunicorn`` and with ``DEBUG=False``. Here's how you do that.

First start a ``bash`` shell with service ports::

  $ docker compose run --service-ports webapp shell

Then compile the static assets::

  app@socorro:/app$ cd webapp/
  app@socorro:/app/webapp$ ./manage.py collectstatic --noinput
  app@socorro:/app/webapp$ cd ..

Now run the webapp with ``gunicorn`` and ``DEBUG=False``::

  app@socorro:/app$ DEBUG=False bash bin/run_webapp.sh

You will now be able to open ``http://localhost:8000`` on the host and if you
view the source you see that the minified and concatenated static assets are
served instead.

Because static assets are compiled, if you change JS or CSS files, you'll need
to re-run ``./manage.py collectstatic``.


Running in a server environment
===============================

Add configuration to ``webapp.env`` file.

Run the docker image using the ``webapp`` command. Something like this::

    docker run \
        --env-file=webapp.env \
        mozilla/socorro_app webapp
