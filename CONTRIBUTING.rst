============
Contributing
============

Code of Conduct
===============

This project and repository is governed by Mozilla's code of conduct and
etiquette guidelines. For more details please see the `CODE_OF_CONDUCT.md file
<https://github.com/mozilla-services/socorro/blob/main/CODE_OF_CONDUCT.md>`_.


Bugs
====

All bugs are tracked in `<https://bugzilla.mozilla.org/>`_.

Write up a new bug:

https://bugzilla.mozilla.org/enter_bug.cgi?product=Socorro&component=General

If you want to do work for which there is no bug, it's best to write up a bug
first. Maybe the ensuing conversation can save you the time and trouble
of making changes!


Pull requests
=============

Pull request summary should indicate the bug the pull request addresses. For
example::

  fix bug nnnnnnn: removed frob from tree class


Pull request descriptions should cover at least some of the following:

1. what is the issue the pull request is addressing?
2. why does this pull request fix the issue?
3. how should a reviewer review the pull request?
4. what did you do to test the changes?
5. any steps-to-reproduce for the reviewer to use to test the changes


Code reviews
============

Pull requests should be reviewed before merging.

Style nits should be covered by linting as much as possible.

Code reviews should review the changes in the context of the rest of the system.


Preparing to contribute changes to Socorro
==========================================

If you're interested in helping out and taking a bug to work on, you
need to do the following first:

1. `Set up a working local development environment
   <https://socorro.readthedocs.io/en/latest/localdevenvironment.html>`_.

2. Read through the `overview of Socorro
   <https://socorro.readthedocs.io/en/latest/overview.html>`_.

We can't assign bugs to you until you've done at least those two
steps.

If you need help, let us know by `sending an email to the mailing list
<https://socorro.readthedocs.io/en/latest/#project-info>`_.


Conventions
===========

Python code conventions
-----------------------

All Python code files should have an MPL v2 header at the top::

  # This Source Code Form is subject to the terms of the Mozilla Public
  # License, v. 2.0. If a copy of the MPL was not distributed with this
  # file, You can obtain one at http://mozilla.org/MPL/2.0/.


We use `black <https://black.readthedocs.io/en/stable/>`_ to reformat Python
code.

To lint the code::

  $ make lint


If you hit issues, use ``# noqa``.

To run the reformatter::

  $ make lintfix


HTML conventions
----------------

2-space indentation.


Javascript code conventions
---------------------------

2-space indentation.

If in doubt, see https://github.com/mozilla-services/socorro/blob/main/.editorconfig


Git conventions
---------------

First line is a summary of the commit. It should start with::

  bug nnnnnnn: summary


After that, the commit should explain *why* the changes are being made and any
notes that future readers should know for context or be aware of.


Migrations
==========

Database migrations (Django)
----------------------------

We use Django's ORM and thus we do database migrations using Django's
migration system.

Do this::

    $ make shell
    app@socorro:/app$ cd webapp-django
    app@socorro:/app/webapp-django$ ./manage.py makemigration --name "BUGID_desc" APP


Elasticsearch migrations (Elasticsearch)
----------------------------------------

We don't do migrations of Elasticsearch data. The system creates a new index
every week, so any changes to new fields or mappings will be reflected the
next time it creates an index.


Dependencies
============

Python Dependencies
-------------------

Python dependencies for all parts of Socorro are split between two files:

1. ``requirements/default.txt``, containing dependencies that Socorro uses
   directly.
2. ``requirements/constraints.txt``, containing dependencies required by the
   dependencies in ``default.txt`` that Socorro does not use directly.

Dependencies in both files must be pinned and hashed. Use
`hashin <https://pypi.python.org/pypi/hashin>`_.

For example, to add ``foobar`` version 5::

  $ hashin -r requirements/default.txt foobar==5

If ``foobar`` has any dependencies that would also be installed, you must add
them to the constraints file::

  $ hashin -r requirements/constraints.txt bazzbiff==4.0

Then rebuild your docker environment::

  $ make build

If there are problems, it'll tell you.

.. Note::

   If you're unsure what dependencies to add to the constraints file, the error
   from running ``make build`` should include a list of dependencies that were
   missing, including their version numbers and hashes.


JavaScript Dependencies
-----------------------

Frontend dependencies for the webapp are in ``webapp-django/package.json``. They
must be pinned and included in
`package-lock.json <https://docs.npmjs.com/files/package-locks>`_.

You can add new dependencies using ``npm`` (you must use version 5 or higher)::

  $ npm install --save-exact foobar@1.0.0

Then rebuild your docker environment::

  $ make build

If there are problems, it'll tell you.


Documentation
=============

Documentation for Socorro is build with `Sphinx
<http://www.sphinx-doc.org/en/stable/>`_ and is available on ReadTheDocs. API is
automatically extracted from docstrings in the code.

To build the docs, run this::

  $ make docs


Testing
=======

Running tests
-------------

The tests in ``socorro/unittests/`` use `pytest <https://pytest.org/>`_.

The tests in ``webapp-django/`` use `pytest <https://pytest.org/>`_.

To run the tests, do::

  $ make test


That runs the ``/app/docker/run_test.sh`` script in the webapp container using
test configuration.

To run specific tests or specify arguments, you'll want to start a shell in the
test container::

  $ make testshell


Then you can run pytest or the webapp tests as you like.

Running all the unittests::

  app@socorro:/app$ pytest


Running a directory of unittests::

  app@socorro:/app$ pytest socorro/unittest/processor/


Running a file of unittests::

  app@socorro:/app$ pytest socorro/unittest/processor/test_processor_app.py


Running webapp tests (make sure you run ``./manage.py collectstatic`` first)::

  app@socorro:/app/webapp-django$ ./manage.py test


Running a directory of webapp tests::

  app@socorro:/app/webapp-django$ ./manage.py test crashstats/home/tests/


Running a file of tests::

  app@socorro:/app/webapp-django$ ./manage.py test crashstats/home/tests/test_views.py


Writing tests
-------------

For webapp tests, put them in the ``tests/`` directory of the appropriate app in
``webapp-django/``.

For other tests, put them in ``socorro/unittest/``.


Repository structure
====================

If you clone our `git repository
<https://github.com/mozilla-services/socorro>`_, you will find the following
folders.

Here is what each of them contains:

**docker/**
    Docker environment related scripts, configuration, and other bits.

**docs/**
    Documentation of the Socorro project (you're reading it right now).

**requirements/**
    Files that hold Python library requirements information.

**scripts/**
    Arbitrary scripts.

**socorro/**
    The bulk of the Socorro source code.

**webapp-django/**
    The webapp source code.
