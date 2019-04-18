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

In order to authenticate in the webapp using the "Login" button, you
need to add the following entry to your ``/etc/hosts`` (or equivalent) file::

  127.0.0.1 oidcprovider

This allows your host machine to properly handle the authentication provided by
the `oidcprovider` docker container.

When logging in with ``oidcprovider``, use the "Sign up" workflow to create a
fake account:

* Username: A non-email username
* Email: Matches your Socorro account email
* Password: Any password

The OIDC user is stored in the ``oidcprovider`` docker container, and will need
to be recreated on restart.


Permissions, User and Groups
============================

Accessing certain parts of the webapp requires that the user is signed-in and
also in a group that contains the required permissions. Users, Groups, and
Permissions are provided by Django, and the documentation for
`User authentication in Django <https://docs.djangoproject.com/en/2.2/topics/auth/>`_
is useful for understanding how it works.

In addition to the Django's auto-generated permissions, Socorro defines
permissions that are used for buisness logic, such as controlling access to
sensitive data. These are assigned to a small number of groups, and users are
assigned to the groups to grant access. The Socorro permissions are listed
(by verbose name) when you visit the
`Your Permissions <https://crash-stats.mozilla.com/permissions/>`_ page.

Maintainers can also be a *superusers*, which means they are implicitly granted
all permissions, and *staff*, which means they can access the Django admin.

Administering Users and Groups
------------------------------
The Django admin can be used to assign a user to a group, in order to grant
them additional access in the web app.

The admin can also be used to create new groups with associated permissions.
However, since groups and permissions are stored in the database, additional
work is needed to apply these changes to all environments.

Changing Groups and Permissions
-------------------------------
The Socorro groups and their permissions are defined in
``webapp-django/crashstats/crashstats/signals.py``. These are applied to
the database in a "post-migrate" signal handler when you run::

   make shell
   webapp-django/manage,py migrate auth

This is run on every deploy, and because it's idempotent, it can be run
repeatedly without creating any duplicates.

.. Note::

  Removing a permission for this file (assuming you know it's never
  referenced anywhere else) will **not** delete it from the database. This will
  require special database manipulation.

To add a new permission for something else, extend ``signal.py`` with a
code name, verbose name, and any group assignments. Run ``./manage.py migrate``
to apply it to the database and make the permission available in code.

Here's how you would use a permission ``save_search`` in a view::

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


When you add a new permission via ``signal.py``, it will automatically appear
on the `Your Permissions <https://crash-stats.mozilla.com/permissions/>`_ page
for the users in that group.


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
