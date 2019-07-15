.. _webapp-chapter:

===========================
Service: Crash Stats Webapp
===========================

Running the webapp
==================

To run the webapp, do::

  $ docker-compose up webapp


That will bring up all the services the webapp requires to run and start the
webapp using the ``/app/docker/run_webapp.sh`` script.

To ease debugging, you can run a shell in the container::

  $ docker-compose run --service-ports webapp shell


Then you can start and stop the webapp, adjust files, and debug.



Setting up authentication and a superuser
=========================================

Creating a superuser
--------------------

If you want to do anything in the webapp admin, you'll need to create a
superuser.

Run this::

  $ docker-compose run app shell ./webapp-django/manage.py makesuperuser email@example.com


You can do this as many times as you like.


Setting up the webapp for OpenID Connect Login
----------------------------------------------

A test OpenID Connect (OIDC) provider is served from the container
``oidcprovider``, and is available at http://oidcprovider.127.0.0.1.nip.io:8080.

When logging in with ``oidcprovider``, use the "Sign up" workflow to create a
fake account:

* Username: A non-email username
* Email: Matches your Socorro account email
* Password: Any password

The OIDC user is stored in the ``oidcprovider`` docker container, and will need
to be recreated on restart.

To automatically create an OIDC account when running ``oidcprovider``, add the
details in ``my.env``::

    OIDC_EMAIL=admin@example.com
    OIDC_USERNAME=admin
    OIDC_PASSWORD=password

You can then skip the "Sign up" workflow and use the "Log in" workflow.

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
``webapp-django/crashstats/crashstats/signals.py``. These are applied to
the database in a "post-migrate" signal handler.


Static Assets
=============
In the development environment, the ``STATIC_ROOT`` is set to
``/tmp/crashstats-static/`` rather than ``/app/webapp-django/static``.
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
in a ``docker-compose.override.yml`` file:

.. code-block:: yaml

    version: "2"
    services:
      webapp:
        volumes:
          # Persist the static files folder
          - ./static:/tmp/crashstats-static

Production-style Assets
-----------------------

When you run ``docker-compose up webapp`` in the local development environment,
it starts the web app using Django's ``runserver`` command. ``DEBUG=True`` is
set in the ``docker/config/never_on_a_server.env`` file, so static assets are
automatically served from within the individual Django apps rather than serving
the minified and concatenated static assets you'd get in a production-like
environment.

If you want to run the web app in a more "prod-like manner", you want to run the
webapp using ``gunicorn`` and with ``DEBUG=False``. Here's how you do that.

First start a ``bash`` shell with service ports::

  $ docker-compose run --service-ports webapp shell

Then compile the static assets::

  app@socorro:/app$ cd webapp-django/
  app@socorro:/app/webapp-django$ ./manage.py collectstatic --noinput
  app@socorro:/app/webapp-django$ cd ..

Now run the webapp with ``gunicorn`` and ``DEBUG=False``::

  app@socorro:/app$ DEBUG=False bash docker/run_webapp.sh

You will now be able to open ``http://localhost:8000`` on the host and if you
view the source you see that the minified and concatenated static assets are
served instead.

Because static assets are compiled, if you change JS or CSS files, you'll need
to re-run ``./manage.py collectstatic``.
