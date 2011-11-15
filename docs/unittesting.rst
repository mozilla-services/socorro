.. index:: unittesting

.. _unittesting-chapter:


Unit Testing
============

There are (some, and a growing number of) unit tests for the Socorro code

How to Unit Test
----------------

* configure your test environment (see below)
* install nosetests
* cd to socorro/unittests
* chant nosetests and observe the result
    * You should expect more than 185 tests (186 as of 2009-03-25)
    * You should see exactly two failures (unless you are running as
      root), with this assertion: AssertionError: You must run this test
      as root (don't forget root's PYTHONPATH)::

        ERROR: testCopyFromGid (socorro.unittest.lib.testJsonDumpStorageGid.TestJsonDumpStorageGid)
        ERROR: testNewEntryGid (socorro.unittest.lib.testJsonDumpStorageGid.TestJsonDumpStorageGid)

* You may 'observe' the result by chanting ``nosetests > test.out 2>&1``
  and then examining test.out (or any name you prefer)
* There is a bash shell file: socorro/unittest/red which may sourced
  to provide a bash function red that simplifies watching test
  logfiles in a separate terminal window. In that window, cd to the
  unittest sub-directory of interest, then source the file: . ../red,
  then chant red. The effect is to clear the screen, then tail -F the
  logfile associated with tests in that directory. You may chant red
  --help to be reminded.
* The red file also provides a function noseErrors which simplifies
  the examination of nosetests output. Chant noseErrors --help for a
  brief summary.

How to write Unit Tests
-----------------------

Nose provides some nice tools. Some of the tests require nose and
nosetests (or a tool that mimics its behavior) However, it is also
quite possible to use Python's unittest. No tutorial here. Instead,
take a look at an existing test file and do something usefully
similar.

Where to write Unit Tests
-------------------------

To maintain the current test layout, note that for every directory
under socorro, there is a same-name directory under socorro/unittest
where the test code for the working directory should be placed. In
addition, there is unittest/testlib that holds a library of useful
testing code as well as some tests for that library.

If you add a unittest subdirectory holding new tests, you must also
provide init.py which may be empty, or nosetests will not enter the
directory looking for tests.

How to configure your test environment
--------------------------------------

* You must have a working postgresql installation see :ref:`installation-chapter` for
  version. It need not be locally hosted, though if not, please be
  careful about username and password for the test user. Also be careful
  not to step on a working database: The test cleanup code drops tables.
* You must either provide for a postgreql account with name and
  password that matches the config file or edit the test config file
  to provide an appropriate test account and password. That file is
  socorro/unittest/config/commonconfig.py. If you add a new test config
  file that needs database access, you should import the details from
  commonconfig, as exemplified in the existing config files.
* You must provide a a database appropriate for the test user
  (default: test. That database must support PLPGSQL. As the owner of
  the test database, while connected to that database, invoke ``CREATE
  LANGUAGE PLPGSQL;``
* You must have installed `nose and nosetests
  <http://code.google.com/p/python-nose/>`_; nosetests should be on
  your PATH and the nose code/egg should be on your PYTHONPATH
* You must have installed the `psycopg2 <http://initd.org/>`_ python
  module
* You must adjust your PYTHONPATH to include the directory holding
  soccoro. E.g if you have installed socorro at
  ``/home/tester/Mozilla/socorro`` then your PYTHONPATH should look like
  ``...:/home/tester/Mozilla:/home/tester/Mozilla/thirdparty:...``
