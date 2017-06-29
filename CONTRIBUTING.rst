============
Contributing
============

Bugs
====

All bugs are tracked in `<https://bugzilla.mozilla.org/>`_.

Write up a new bug:

FIXME(willkg): Link to write up a new bug.


Docker
======

Everything runs in a Docker container. Thus Socorro requires fewer things to get
started and you're guaranteed to have the same setup as everyone else and it
solves some other problems, too.

If you're not familiar with `Docker <https://docs.docker.com/>`_ and
`docker-compose <https://docs.docker.com/compose/overview/>`_, it's worth
reading up on.


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

  Fixes bug nnnnnnn

or::

  Bug nnnnnnn


The first, when it lands, will cause the bug to be closed. The second one does not.

After that, the commit should explain *why* the changes are being made and any
notes that future readers should know for context or be aware of.


Pull requests
=============

Pull request summary should indicate the bug the pull request addresses.

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


Dependencies
============

Dependencies for all parts Socorro are in ``requirements.txt``. They need to be
pinned and hashed. Use `hashin <https://pypi.python.org/pypi/hashin>`_.

For example, to add ``foobar`` version 5::

  hashin -r requirements.txt foobar==5

Then rebuild your docker environment::

  make dockerbuild

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

The tests in ``webapp-django/`` use `Nose <https://nose.readthedocs.io/>`_.

To run the tests, do::

  $ make dockertest


That runs the ``/app/docker/run_test.sh`` script in the webapp container using
test configuration.

To run specific tests or specify arguments, you'll want to start a shell in the
test container::

  $ make dockertestshell


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


Writing tests
=============

For webapp tests, put them in the ``tests/`` directory of the appropriate app in
``webapp-django/``.

For other tests, put them in ``socorro/unittest/``.


PostgresSQL tests
-----------------

When is a PostgreSQL test::

  from unittestbase import PostgreSQLTestCase

  # PostgreSQl adapter for Python
  import psycopg2


Mock usage
----------

`Mock <http://www.voidspace.org.uk/python/mock/>`_ is a python library for mocks
objects. This allows us to write isolated tests by simulating services beside
using the real ones.

Once we used our mock object, we can make assertions about how it has been used,
like assert if the something function was called one time with (10,20)
parameters::

  from mock import MagicMock
  from socorro.unittest.testbase import TestCase

  class TestClass(TestCase):

      def method(self):
          self.something(10, 20)

      def test_something(self, a, b):
          pass

  mocked = TestClass()
  mocked.test_something = MagicMock()
  mocked.method()
  mocked.test_something.assert_called_once_with(10, 20)

The above example doesn't print anything because assert had passed, but if we
call the function below, we will receive an error::

  mocked.test_something.assert_called_once_with(10, 30)
  > AssertionError: Expected call: mock(10, 30)
  > Actual call: mock(10, 20)

Some other similar functions are ``assert_any_call()``,
``assert_called_once_with()``, ``assert_called_with()`` and
``assert_has_calls()``.

The following is a more complex example about using mocks, which simulates a
database and can be found at Socorro's source code. It tests a ``KeyError``
exception while saving a broken processed crash::

  def test_basic_key_error_on_save_processed(self):

      mock_logging = mock.Mock()
      mock_postgres = mock.Mock()
      required_config = PostgreSQLCrashStorage.required_config
      required_config.add_option('logger', default=mock_logging)

      config_manager = ConfigurationManager(
        [required_config],
        app_name='testapp',
        app_version='1.0',
        app_description='app description',
        values_source_list=[{
          'logger': mock_logging,
          'database_class': mock_postgres
        }]
      )

      with config_manager.context() as config:
          crashstorage = PostgreSQLCrashStorage(config)
          database = crashstorage.database.return_value = mock.MagicMock()
          self.assertTrue(isinstance(database, mock.Mock))

          broken_processed_crash = {
              "product": "Peter",
              "version": "1.0B3",
              "ooid": "abc123",
              "submitted_timestamp": time.time(),
              "unknown_field": 'whatever'
          }
          assert_raises(
              KeyError,
              crashstorage.save_processed,
              broken_processed_crash
          )


Mocking with decorators
-----------------------

We can use ``@patch`` if we want to patch with a Mock. This way the
mock will be created and passed into the test method ::

  class TestClass(unittest.TesCase):

     @mock.patch('package.module.ClassName')
     def test_something(self, MockClass):

        assert_true(package.module.ClassName is MockClass)
