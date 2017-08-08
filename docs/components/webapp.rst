.. _webapp-chapter:

=================================
Webapp (crash-stats analysis app)
=================================

Running the webapp
==================

To run the webapp using the webapp configuration, do::

  $ docker-compose up webapp


That will bring up all the services the webapp requires to run and start the
webapp using the ``/app/docker/run_webapp.sh`` script using the webapp
configuration.

To ease debugging, you can run a shell in the container::

  $ docker-compose run webapp /bin/bash


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


FIXME(willkg): Review everything after this line.


Setting up authentication and a superuser
=========================================

Creating a superuser
--------------------

If you want to do anything in the webapp admin, you'll need to create a
superuser.

Run this::

  $ docker-compose run webapp python webapp-django/manage.py makesuperuser email@example.com


You can do this as many times as you like.


Setting up the webapp for Google Sign-In
----------------------------------------

In order to authenticate in the webapp using the "Google signin" button, you
need to get a set of oauth credentials.

1. Go to https://console.developers.google.com/apis/credentials

2. Create a project

3. Set up credentials

   :authorized js origin: http://localhost:8000/
   :callback url: http://localhost:8000/oauth2/signin/

4. Open ``webapp-django/.env`` in an editor and add these lines::

       OAUTH2_CLIENT_ID=<client id>
       OAUTH2_CLIENT_SECRET=<secret>

   where ``<client id>`` is the oauth client id and ``<secret>`` is the oauth
   client secret that you got from step 3


After that, Google Sign-In should work.


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
