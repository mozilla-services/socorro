.. index:: webapp

.. _webapp-chapter:

Webapp
======


About Permissions, User and Groups
----------------------------------

Accessing certain parts of the webapp requires that the user is not
only signed-in but also belongs to a group that contains certain
permissions.

Throughout the code, the ``code names`` of the
permissions are hardcoded. However, groups and which permissions
groups have, is all part of the "user generated data" and can and will
change.

A permission always contains a code name, a verbose name and a content
type (aka Django model) that it belongs to. For business logic
specific permissions we use in Socorro to guard certain data that is
not a Django model we use permissions that belong to a blank content
type. These are the permissions that appear in the list when you visit
the `Your Permissions <https://crash-stats.mozilla.com/permissions/>`_
page.


Administering Users and Groups
------------------------------

First of all, to reach the Admin UI at all, you need to be a
``superuser``. This is **not** dependent on any permissions. Being a
superuser means you have ("root like") access to everything. Any
permission check against a superuser user will always return true.

You can create groups freely in the Admin section. And you can attach
any permissions to the groups.

You can **not** give a specific user a specific permission, or
combination of permissions. Instead you have to solve this by
creating, potentially multiple, groups and attach those accordingly to
the user you want to affect.


Extending permissions
---------------------

All current custom permissions we use are defined in the constants at
the top of
``webapp-django/crashstats/crashstats/management/__init__.py``. That
file also defines some default groups.

This file is executed when you run:
::
  cd webapp-django
  export SECRET_KEY="..."
  ./manage.py migrate auth
  ./manage.py migrate

This should be done automatically on every release. Because it's idempotent
it can be run repeatedly without creating any duplicates.

Note: Removing a permission for this file (assuming you know it's
never referenced anywhere else) will **not** delete it from the
database. This will require special database manipulation.

To add a new permission for something else, extend that above
mentioned file as per how it's currently layed out. You'll need to
come up with a code name  and a verbose name. For example, a
permission for being allowed to save searches could be::

    code name: save_search
    verbose name: Save User Searches

Then, once that's added to the file run ``./manage.py migrate``
and it will be ready to depend on in the code.

Here's for example how you use this permission in a view::

    def save_search(request):
        if not request.user.has_perm('crashstats.save_search'):
	    return http.HttpResponseForbidden('Not allowed!')

Note the added ``crashstats.`` prefix added to the code name when
using the ``user.has_perm()`` function.

Here's an example in a template::

    {% if request.user.has_perm('crashstats.save_search') %}
    <form action="{{ url('crashstats:save_search') }}" method="post">
    <button>Save this search</button>
    </form>
    {% endif %}


When you add a new permission here they will automatically appear on
the `Your Permissions <https://crash-stats.mozilla.com/permissions/>`_
page.

Content-level permissions
-------------------------

This does not exist. You can't define certain permissions on only
certain crashes.

If you need permissions that depend on the content you'll need to
write it yourself with some conditionals.

Trouble logging in with Persona?
--------------------------------

If you have set up your webapp but you can't sign in, it could very well
be because some configuration is wrong compared to how you're running
the webapp.

If this is the problem go to ``http://localhost:8000/_debug_login``.

This works for both production and development. If you're running in
production you might not be using ``localhost:8000`` so all you need
to remember is to go to ``/_debug_login`` on whichever domain you
will use in production.
