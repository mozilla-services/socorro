============
Contributing
============

Bugs
====

All bugs are tracked in `<https://bugzilla.mozilla.org/>`_.

Write up a new bug:

https://bugzilla.mozilla.org/enter_bug.cgi?product=Socorro

There are multiple components to choose. If in doubt use ``General``.


Docker
======

Everything runs in a Docker container. Thus Socorro requires fewer things to get
started and you're guaranteed to have the same setup as everyone else and it
solves some other problems, too.

If you're not familiar with `Docker <https://docs.docker.com/>`_ and
`docker-compose <https://docs.docker.com/compose/overview/>`_, it's worth
reading up on.


Preparing to contribute changes to Socorro
==========================================

If you're interested in helping out and taking a bug to work on, you
need to do the following first:

1. `Set up a working local development environment
   <https://socorro.readthedocs.io/en/latest/gettingstarted.html>`_.

2. Read through the `overview of Socorro
   <https://socorro.readthedocs.io/en/latest/overview.html>`_.

We can't assign bugs to you until you've done at least those two
steps.

If you need help, let us know by `asking on IRC or sending an email to the
mailing list <https://socorro.readthedocs.io/en/latest/#project-info>`_.


Python code conventions
=======================

All Python code files should have an MPL v2 header at the top::

  # This Source Code Form is subject to the terms of the Mozilla Public
  # License, v. 2.0. If a copy of the MPL was not distributed with this
  # file, You can obtain one at http://mozilla.org/MPL/2.0/.


Python code should follow PEP-8.

Max line length is 100 characters.

4-space indentation.

To run the linter, do::

  $ make lint


If you hit issues, use ``# noqa``.


Javascript code conventions
===========================

4-space indentation.

If in doubt, see https://github.com/mozilla-services/socorro/blob/master/.editorconfig


Git conventions
===============

First line is a summary of the commit. It should start with one of the following::

  bug nnnnnnn: summary

which will trigger the auto-closer to add a comment to the bug when this is merged
into the master branch, or::

  fix bug nnnnnnn: summary

which will do that and also close the bug.

After that, the commit should explain *why* the changes are being made and any
notes that future readers should know for context or be aware of.


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


Python Dependencies
===================

Python dependencies for all parts of Socorro are split between two files:

1. ``requirements/default.txt``, containing dependencies that Socorro uses
   directly.
2. ``requirements/constraints.txt``, containing dependencies required by the
   dependencies in ``default.txt`` that Socorro does not use directly.

Dependencies in both files must be pinned and hashed. Use
`hashin <https://pypi.python.org/pypi/hashin>`_.

For example, to add ``foobar`` version 5::

  hashin -r requirements/default.txt foobar==5

If ``foobar`` has any dependencies that would also be installed, you must add
them to the constraints file::

  hashin -r requirements/constraints.txt bazzbiff==4.0

Then rebuild your docker environment::

  make build

If there are problems, it'll tell you.

.. note:: If you're unsure what dependencies to add to the constraints file,
   the error from running ``make build`` should include a list of
   dependencies that were missing, including their version numbers and hashes.


JavaScript Dependencies
=======================

Frontend dependencies for the webapp are in ``webapp-django/package.json``. They
must be pinned and included in
`package-lock.json <https://docs.npmjs.com/files/package-locks>`_.

You can add new dependencies using ``npm`` (you must use version 5 or higher):

  npm install --save-exact foobar@1.0.0

Then rebuild your docker environment::

  make build

If there are problems, it'll tell you.


Documentation
=============

Documentation for Socorro is build with `Sphinx
<http://www.sphinx-doc.org/en/stable/>`_ and is available on ReadTheDocs. API is
automatically extracted from docstrings in the code.

To build the docs, run this:

.. code-block:: shell

    $ make docs


Running tests
=============

The tests in ``socorro/unittests/`` use `pytest <https://pytest.org/>`_.

The tests in ``webapp-django/`` use `pytest <https://pytest.org/>`_.

The tests in ``webapp-django/staticfiles`` use `Jest <https://jestjs.io/>`_.

To run the tests, do::

  $ make test


That runs the ``/app/docker/run_test.sh`` script in the webapp container using
test configuration.

To run specific tests or specify arguments, you'll want to start a shell in the
test container::

  $ make testshell


Then you can run pytest or the webapp tests as you like.

Running all the unittests::

  app@...:/app$ pytest


Running a directory of unittests::

  app@...:/app$ pytest socorro/unittest/processor/


Running a file of unittests::

  app@...:/app$ pytest socorro/unittest/processor/test_processor_app.py


Running webapp tests (make sure you run ``./manage.py collectstatic`` first)::

  app@...:/app/webapp-django$ ./manage.py test


Running a directory of webapp tests::

  app@...:/app/webapp-django$ ./manage.py test crashstats/home/tests/


Running a file of tests::

  app@...:/app/webapp-django$ ./manage.py test crashstats/home/tests/test_views.py

Running the staticfiles Jest tests and watching for changes::

  app@...:/app/webapp-django$ /webapp-frontend-deps/node_modules/.bin/jest staticfiles/ --watch


Writing tests
=============

For webapp tests, put them in the ``tests/`` directory of the appropriate app in
``webapp-django/``.

For webapp/staticfiles tests, put unit tests in the same folder as the component
that they are testing

For other tests, put them in ``socorro/unittest/``.


Mock usage
----------

`Mock <http://www.voidspace.org.uk/python/mock/>`_ is a python library for mocks
objects. This allows us to write isolated tests by simulating services beside
using the real ones. Best examples is existing tests which admittedly do mocking
different depending on the context.

Tip! Try to mock in limited context so that individual tests don't affect other
tests. Use context managers and instead of monkey patching imported modules.


Repository structure
====================

If you clone our `git repository
<https://github.com/mozilla-services/socorro>`_, you will find the following
folders.

Here is what each of them contains:

**alembic/**
    Alembic-managed database migrations.

**docker/**
    Docker environment related scripts, configuration, and other bits.

**docs/**
    Documentation of the Socorro project (you're reading it right now).

**e2e-tests/**
    The Selenium tests for the webapp.

**minidump-stackwalk/**
    The minidump stackwalker program that the processor runs for pulling
    out information from crash report dumps.

**requirements/**
    Files that hold Python library requirements information.

**scripts/**
    Arbitrary scripts.

**socorro/**
    The bulk of the Socorro source code.

**webapp-django/**
    The webapp source code.
