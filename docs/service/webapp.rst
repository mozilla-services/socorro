.. _webapp-chapter:

==================
Crash Stats Webapp
==================

Code is in ``webapp/``.

Run script is ``/app/bin/run_service_webapp.sh``.


Running in a local dev environment
==================================

This documentation assumes you've gone through the setup steps described in the
Development chapter :ref:`setup-quickstart`, in particular:

.. code-block:: shell

   $ just build
   $ just setup

To run the webapp:

.. code-block:: shell

   $ docker compose up webapp

or if you don't like typing:

.. code-block:: shell

   $ just run

To ease debugging, you can run a shell in the container:

.. code-block:: shell

   $ docker compose run --service-ports webapp shell

Then you can start and stop the webapp, adjust files, and debug.  The webapp
runs ESBuild's watch mode and Django's StatReloader to reload static file
changes automatically. This avoids needing to stop, rebuild, and restart the
container/server on every change to static files. 
Note that changes to ``esbuild.js`` and other config files may still require stop/rebuild/restart.


Static Assets
=============

Static assets (JS, CSS, images, fonts) are collected and processed by ESBuild. 
Because we host Django admin pages, we also rely on the collectstatic package
for assets that belong to those internal admin pages. There is minor overlap between ESBuild and collectstatic, 
particarly relating to images/fonts. However, main site development involves only ESBuild.

Static asset builds are triggered by NPM scripts in ``webapp/package.json``.
The assets are built into ``/app/webapp/static`` also known as ``STATIC_ROOT``.

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

If you want to do anything in the webapp admin, or use superuser features like Customize in Super Search, you'll need to create a
superuser in the Crash Stats webapp and a OIDC account to authenticate against
in the oidcprovider service container. This is done automatically as part of ``just setup`` (see :ref:`setup-quickstart`), but it can also be run separately via::
   bin/create_superuser.sh

As the output indicates, this creates a superuser in Crash Stats with:

* username: admin
* password: admin
* email: admin@example.com

To log into Crash Stats, start up the webapp via ``just run``, click Login, and use these credentials.

.. Note::

   You will have to recreate both of these accounts any time you do something
   that recreates the postgres db or restarts the oidcprovider service
   container.


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
