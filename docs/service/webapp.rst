.. _webapp-chapter:

===========================
Service: Crash Stats Webapp
===========================

Running the webapp
==================

To run the webapp, do::

  $ docker-compose up webapp webpack


That will bring up all the services the webapp requires to run and start the
webapp using the ``/app/docker/run_webapp.sh`` script.

To ease debugging, you can run a shell in the container::

  $ docker-compose run --service-ports webapp shell


Then you can start and stop the webapp, adjust files, and debug.


.. Note::

   The ``STATIC_ROOT`` is set to ``/tmp/crashstats-static/`` rather than
   ``/app/webapp-django/static``. This alleviates permissions-related problems
   because the process in the container runs as uid 10001 which is not the uid
   of the user you're using on your host computer.

   The problem this creates is that ``/tmp/crashstats-static/`` is ephemeral
   and any changes there disappear when you stop the container.

   If you want it persisted, you should mount that directory using ``volumes``
   in a ``docker-compose.override.yml`` file.

   https://docs.docker.com/compose/extends/

.. note::

   The ``webpack`` service watches for changes to certain frontend files and
   rebuilds bundles when they change. If you make changes to the Webpack
   config, you must restart the service for the changes to take effect.

   If the ``webpack`` service is not running, certain pages may not update when
   you change the frontend files they rely on.



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

In order to authenticate in the webapp using the "Login" button, you
need to add the following entry to your ``/etc/hosts`` (or equivalent) file::

  127.0.0.1 oidcprovider

This allows your host machine to properly handle the authentication provided by
the `oidcprovider` docker container.


About Permissions, User and Groups
==================================

Accessing certain parts of the webapp requires that the user is signed-in and
also in a group that contains the required permissions.

A permission consists of a code name, a verbose name and a content type (aka
Django model) that it belongs to. For business logic specific permissions we use
in Socorro to guard certain data that is not a Django model we use permissions
that belong to a blank content type. These are the permissions that appear in
the list when you visit the `Your Permissions
<https://crash-stats.mozilla.com/permissions/>`_ page.


Administering Users and Groups
==============================

To see the admin user interface, you need to be a superuser. This is not
dependent on any permissions. Being a superuser means you have root-like access
to everything. Any permission check against a superuser user will always return
true.

You can create groups freely in the Admin section and you can attach any
permissions to the groups.

You can not give a specific user a specific permission, or combination of
permissions. Instead you have to solve this by creating, potentially multiple,
groups and attach those accordingly to the user you want to affect.


Extending permissions
=====================

All current custom permissions we use are defined in the constants at the top of
``webapp-django/crashstats/crashstats/management/__init__.py``. That file also
defines some default groups.

This file is executed when you run:

::

   cd webapp-django
   export SECRET_KEY="..."
   ./manage.py migrate auth
   ./manage.py migrate


This is run on every deploy because it's idempotent it can be run repeatedly
without creating any duplicates.

Note: Removing a permission for this file (assuming you know it's never
referenced anywhere else) will **not** delete it from the database. This will
require special database manipulation.

To add a new permission for something else, extend that above mentioned file as
per how it's currently layed out. You'll need to come up with a code name and a
verbose name. For example, a permission for being allowed to save searches could
be:

:code name:    save_search
:verbose name: Save User Searches


Then, once that's added to the file, run ``./manage.py migrate`` and it will be
ready to depend on in the code.

Here's how you might use this permission in a view::

  def save_search(request):
      if not request.user.has_perm('crashstats.save_search'):
	  return http.HttpResponseForbidden('Not allowed!')


Note the added ``crashstats.`` prefix added to the code name when using the
``user.has_perm()`` function.

Here's an example in a template::

  {% if request.user.has_perm('crashstats.save_search') %}
    <form action="{{ url('crashstats:save_search') }}" method="post">
      <button>Save this search</button>
    </form>
  {% endif %}


When you add a new permission here they will automatically appear on the `Your
Permissions <https://crash-stats.mozilla.com/permissions/>`_ page.


Troubleshooting
===============

If you have set up your webapp but you can't sign in, it could very well be
because some configuration is wrong compared to how you're running the webapp.

If this is the problem go to ``http://localhost:8000/_debug_login``.

This works for both production and development. If you're running in production
you might not be using ``localhost:8000`` so all you need to remember is to go
to ``/_debug_login`` on whichever domain you will use in production.

If web services are not starting up, ``/var/log/nginx/`` is a good place to
look.

If you are not able to log in to the crash-stats UI, try hitting
``http://crash-stats/_debug_login``

If you are having problems with crontabber jobs, this page shows you the
state of the dependencies: ``http://crash-stats/crontabber-state/``

If you're seeing "Internal Server Error", you can get Django to send you email
with stack traces by adding this to
``/data/socorro/webapp-django/crashstats/settings/base.py``:

::

  # Recipients of traceback emails and other notifications.
  ADMINS = (
      ('Your Name', 'your_email@domain.com'),
  )
  MANAGERS = ADMINS


Running Web App in a Prod-like Way
==================================

When you run ``docker-compose up webapp`` in the local development environment,
it starts the web app using Django's ``runserver`` command. ``DEBUG=True`` is
set in the ``docker/config/never_on_a_server.env`` file, so static assets are
automatically served from within the individual Django apps rather than serving
the minified and concatenated static assets you'd get in a production-like
environment.

If you want to run the web app in a more "prod-like manner", you want to run the
webapp using ``uwsgi`` and with ``DEBUG=False``. Here's how you do that.

First start a ``bash`` shell with service ports::

  $ docker-compose run --service-ports webapp shell

Then compile the static assets::

  app@socorro:/app$ cd webapp-django/
  app@socorro:/app/webapp-django$ ./manage.py collectstatic --noinput
  app@socorro:/app/webapp-django$ cd ..

Now run the webapp with ``uwsgi`` and ``DEBUG=False``::

  app@socorro:/app$ DEBUG=False bash docker/run_webapp.sh

You will now be able to open ``http://localhost:8000`` on the host and if you
view the source you see that the minified and concatenated static assets are
served instead.

Because static assets are compiled, if you change JS or CSS files, you'll need
to re-run ``./manage.py collectstatic``.
