.. index:: unittesting

.. _unittesting-chapter:


Socorro Unit Tests
==================

Before testing, you must have a working Socorro by performing :ref:`installation-chapter` steps.

Requirements
````````````
It is necessary that the PostgreSQL database is working. It need not be locally hosted, though if not, please be careful about username and password for the test user. Also be careful not to step on a working database: The test cleanup code drops tables.

The unit tests use `Nose <https://nose.readthedocs.org/en/latest/>`_, a nicer testing for python which extends unittest to making testing easier::

  pip install nose

`PEP8 <http://www.python.org/dev/peps/pep-0008/>`_ is a style guide that aims to improve the readability of code and make it consistent. It is important use it to guarantee that the written test pass in jenkins ::

  pip install pep8

How to Unit Test
````````````````

Settings before testing
---------------------------------

Setting up the virtual environment::
 
  make virtualenv
  . socorro-virtualenv/bin/activate
  export PYTHONPATH=.

Setting up database and other dependencies for tests::
 
  make setup-test

Testing
--------

All socorro tests through Makefile::
 
  make test
    
All socorro unit tests::
 
  nosetests socorro/unittest/

Specific module::
 
  nosetests socorro/unittest/module

Specific file::
 
  nosetests socorro/unittest/module/test_file.py

Specific class::
 
  nosetests socorro/unittest/module/test_file.py:TestClassName

Specific function::
 
  nosetests socorro/unittest/module/test_file.py:TestClassName:test_function


Configuration
-------------

You shouldn't attempt to pass command line arguments to nosetests because it passes them into the test environment which breaks socorro's configuration behavior. Instead, set environment variables or create ~/.noserc with the wanted configurations , for example::

  [nosetests]
  verbosity=2
  with-coverage=1
  cover-package=socorro

Verbosity [NOSE_VERBOSE]
^^^^^^^^^^^^^^^^^^^^^^^^

This command will set the level of verbosity. 4=all, 3=no script, 2=no info, 1=no warnings, 0=none. The default is verbosity=1. 

Coverage [NOSE_WITH_COVERAGE] 
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The coverage report will cover any python source module imported after the start of the test run. http://nose.readthedocs.org/en/latest/plugins/cover.html

All socorro unit tests coverage::

  nosetests socorro --with-coverage --cover-package=socorro
 
Specific package coverage::

  nosetests socorro/unittest/module --with-coverage --cover-package=socorro.module

Plugin Xunit [NOSE_WITH_XUNIT]
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Provides test results in the standard XUnit XML format.
--with-xunit

Output [NOSE_NOCAPTURE]
^^^^^^^^^^^^^^^^^^^^^^^

To print immediately any stdout output::

  nosetests -s


To retain testing ouput in a file::
 
  nosetests > filename.out 2>&1 


For another configuration
^^^^^^^^^^^^^^^^^^^^^^^^^::

  nosetest -help


What is red?
^^^^^^^^^^^^

There is a bash shell file: socorro/unittest/red which may sourced
to provide a bash function red that simplifies watching test
logfiles in a separate terminal window. In that window, cd to the
unittest sub-directory of interest, then source the file: . ../red,
then chant red. The effect is to clear the screen, then tail -F the
logfile associated with tests in that directory. You may chant red
--help to be reminded.

The red file also provides a function noseErrors which simplifies
the examination of nosetests output. Chant noseErrors --help for a
brief summary.

Where to write Unit Tests
-------------------------

For each socorro directory, there is a same-name directory under socorro/unittest, where the test code for the working directory should be placed. 

If you want add a unittest subdirectory, you must also provide an empty init.py, or nosetests will not enter the directory looking for tests. 

How to write Unit Tests
-----------------------

Recommendations
^^^^^^^^^^^^^^^

1) The attribute documentation strings (a.k.a. docstrings) should be written conform to PEP257, containing the test/class description
::
  
  def test_something():
  """A brief description about this test.""" - Look this because some files may be using for failling
    
2) Each file should pass PEP8, a style guide for python code:

  * Use 4 spaces per indentation level. 
  * Lines should try not to have more than 79 characters.
  * Be carefull with whitespaces and blank lines.

You can use it as below::

  pep8 test_something.py
  test_something.py:65:11: E401 multiple imports on one line
  test_something.py:77:1: E302 expected 2 blank lines, found 1
  test_something.py:88:5: E301 expected 1 blank line, found 0
  test_something.py:222:34: W602 deprecated form of raising exception
  test_something.py:347:31: E211 whitespace before '('

3) The comments should be on the line above
::

  # Here comes the comment about the list creation
  just_a_list = []

4) Python conventions

  * Class names should be in ``UpperCamelCase``; 
  * Function names should be ``lowercase_separated_by_underscores``; 
  * And constants should be ``CAPITALIZED_WITH_UNDERSCORES``. 

::

  class TestClass():
    """Test a dummy class."""
    
    def test_if_the_function_something_works ():
        """A brief description about this test."""
        
Header
^^^^^^

At the top of each file should have python file header and a completed copy of the MPL2 license block, immediately preceded and followed by an empty line::

  #!/usr/bin/env python
  
  # This Source Code Form is subject to the terms of the Mozilla Public
  # License, v. 2.0. If a copy of the MPL was not distributed with this
  # file, You can obtain one at http://mozilla.org/MPL/2.0/.

Imports :: 
    import unittest

Fixtures
^^^^^^^^

Nose supports fixtures (setup and teardown methods) at the package, module, class, and test level. The setUp always runs before any test (or collection of tests for test packages and modules) and the tearDown runs if setup has completed successfully, no matter the status of the test run. 
  * setUp() method: runs before each test method
  * tearDown() method: runs after each test method 

::
  
  import unittest

  class TestClass(unittest.TestCase):
    
      def setUp(self):
          print "setup"
                
      def tearDown(self):
          print "teardown"
    
      def test_something(self):
          print "inside test_something"
          assert True

If you run the previously code::
        
  $ nosetests test.py -s
  setup
  inside test_something
  teardown
  .
  --------------------
  Ran 1 test in 0.001s
  OK

Testing tools
^^^^^^^^^^^^^

Exceptions
Raise SkipTest
assert

Mock usage
^^^^^^^^^^

Decorators
^^^^^^^^^^

Code readability
^^^^^^^^^^^^^^^^

Some comments using characters can be used to improve the code readability::

  #=============================================================================
  class TestClass(unittest.TestCase):
      """Test a dummy class."""
  
      #-------------------------------------------------------------------------
      def test_something(self):
          """A brief description about this test."""
      
          pass

...............

Old instructions

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
