.. _webapp-chapter:

==================
Crash Stats Webapp
==================

Code is in ``webapp/``.

Run script is ``/app/bin/run_service_webapp.sh``.

Running in a local dev environment
==================================

This documentation assumes you've gone through the setup steps described in the Development chapter :ref:`setup-quickstart`, in particular:

  .. code-block:: shell

      $ just build
      $ just setup

To run the webapp...

  .. code-block:: shell

      $ docker compose up webapp

...or if you don't like typing:

  .. code-block:: shell

      $ just run

To ease debugging, you can run a shell in the container:

  .. code-block:: shell
      $ docker compose run --service-ports webapp shell

Then you can start and stop the webapp, adjust files, and debug.  
The webapp runs ESBuild's watch mode and Django's StatReloader to reload static file changes automatically.
This avoids needing to stop, rebuild, and restart the container/server on every change.

Static Assets
=============

At the time of this writing, JS files are collected and processed by collectstatic and django-pipeline.  All other static assets (CSS, images, fonts, etc) are collected and processed by ESBuild.
Migration of JS to ESBuild is currently in progress, with the intent to retire django-pipeline when complete.  The collectstatic package will continue to be used in support of the internal Django admin pages.

Static asset builds are triggered by NPM scripts in ``webapp/package.json``.  The assets are built into ``/app/webapp/static`` also known as ``STATIC_ROOT``.

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

Compile the static assets (if needed)::

  app@socorro:/app$ npm run build --prefix webapp

Then run the webapp with ``gunicorn`` and ``DEBUG=False``::

  app@socorro:/app$ DEBUG=False bash bin/run_service_webapp.sh

You will now be able to open ``http://localhost:8000`` on the host and if you
view the source you see that the minified and concatenated static assets are
served instead.

Because static assets are compiled, if you change JS or CSS files, you'll need
to re-run ``npm run build --prefix webapp`` - the "watch mode" feature is not enabled in production.

Admin Account
=============

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