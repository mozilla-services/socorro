.. index:: unittesting

.. _unittesting-chapter:


Socorro Unit Tests
==================

Before testing, we must have a working Socorro by
performing :ref:`installation-chapter` steps.

Requirements
````````````

It is necessary to have a working PostgreSQL database. It does not has
to be locally hosted, though if not, please be careful about username
and password for the test user. Also be careful to do not step over a
working database: The test cleanup code drops tables.

The unit tests use `Nose <https://nose.readthedocs.org/en/latest/>`_,
a nicer testing framework for Python which extends unittest to make
testing easier::

  pip install nose

`PEP8 <http://www.python.org/dev/peps/pep-0008/>`_ is a style guide
that aims to improve code readability and make it consistent. It is
important to use it to guarantee that the written test is going to
pass in `Jenkins <http://jenkins-ci.org/>`_ ::

  pip install pep8

How to Unit Test
````````````````

Settings before testing
-----------------------

Setting up the virtual environment::
 
  make virtualenv
  . socorro-virtualenv/bin/activate
  export PYTHONPATH=.

Setting up database and other dependencies of tests::
 
  make setup-test

Testing
--------

All Socorro tests through Makefile::
 
  make test
    
All Socorro unit tests::
 
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

We shouldn't attempt to pass command line arguments to nosetests
because it passes them into the test environment which breaks
socorro's configuration behavior. Instead, lets set environment
variables or create ``~/.noserc`` with desired configurations, for
example::

  [nosetests]
  verbosity=2
  with-coverage=1
  cover-package=socorro

Verbosity [NOSE_VERBOSE]
^^^^^^^^^^^^^^^^^^^^^^^^

This command will set verbosity level: 4=all, 3=no script, 2=no info,
1=no warnings, 0=none. Default is verbosity=1.

Coverage [NOSE_WITH_COVERAGE] 
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The coverage plugin allows us to know what percentage of source code
has been tested. It is also usefull to describe which specific lines
of source code weren't tested yet. It is a `Ned Batchelder’s coverage
module <http://nose.readthedocs.org/en/latest/plugins/cover.html>`_
which reports covers all Python source module imported after the test
start.

All socorro unit tests coverage::

  nosetests socorro --with-coverage --cover-package=socorro
 
Specific package coverage::

  nosetests socorro/unittest/module --with-coverage --cover-package=socorro.module

Plugin Xunit [NOSE_WITH_XUNIT]
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Provides test results in XUnit XML format, designed specially for Jenkins.

Output [NOSE_NOCAPTURE]
^^^^^^^^^^^^^^^^^^^^^^^

To print immediately any stdout output::

  nosetests -s


To retain testing output in a file::
 
  nosetests > filename.out 2>&1 


For another configuration
^^^^^^^^^^^^^^^^^^^^^^^^^
::

  nosetest -help


Where to write Unit Tests
-------------------------

For each socorro directory, there is a directory with the same name
under ``socorro/unittest``, where the test code for the working
directory should be placed.

If we want to add a unittest subdirectory, we must also provide an
empty init.py file, otherwise nosetests will not enter the respective
directory while looking for tests.

How to write Unit Tests
-----------------------

Recommendations
^^^^^^^^^^^^^^^

1) The attribute documentation strings (a.k.a. docstrings) should be
   written conform to PEP257, containing the test/class description
::
  
  def test_something():
  """A brief description about this test."""
    
2) Each file should pass PEP8, a style guide for python code:

  * Use 4 spaces per indentation level. 
  * Lines should try not to have more than 79 characters.
  * Be carefull with whitespaces and blank lines.

We can use the PEP8 plugin as below::

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

First lines of each file should have a Python file header and a
complete copy of the MPL2 license block, immediately preceding and
followed by an empty line::

  #!/usr/bin/env python
  
  # This Source Code Form is subject to the terms of the Mozilla Public
  # License, v. 2.0. If a copy of the MPL was not distributed with this
  # file, You can obtain one at http://mozilla.org/MPL/2.0/.
                                                                           
                                                                           
Usual imports:: 

  import socorro.directory.module
  from nose.tools import *
  from nose.plugins.Attrib import attr
  
When mock objects are needed::

  import mock
    
When is a PostgreSQL test::

  from unittestbase import PostgreSQLTestCase  
  import psycopg2 (PostgreSQl adapter for Python)
  
  
Fixtures
^^^^^^^^

Nose supports fixtures (setup and teardown methods) at the package,
module, class, and test level. The setUp always runs before any test
(or collection of tests for test packages and modules) and the
tearDown runs if setUp has completed successfully, no matter the
status of the test run.
  * setUp() method: runs before each test method
  * tearDown() method: runs after each test method 

::
  
  class TestClass(object):
    
      def setUp(self):
          print "setup"
                
      def tearDown(self):
          print "teardown"
    
      def test_something(self):
          print "inside test_something"
          assert True

If we run the previously code::
        
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

There are many ways to verify if the results are what we originally
expected.

One of this forms is using nose.tools, which provides convenience
functions to make writing tests easier. It includes all assertX
methods of unittest.TestCase spelled in a pythonic way:
``assert_true`` besides ``self.assertTrue``.
::

  from nose.tools import *

  assert expected == received

  assert_false(expr, msg=None)
  assert_true(expr, msg=None)
  eq_(a, b, msg=None) >> Shorthand for ‘assert a == b, “%r != %r” % (a, b)
  ok_(expr, msg=None) >> Shorthand for assert

  assert_equal(first, second, msg=None)
  assert_list_equal(list1, list2, msg=None)
  assert_dict_equal(self, d1, d2, msg=None)
  assert_tuple_equal(self, tuple1, tuple2, msg=None) 

  # difference rounded to the given number of decimal places and
  # comparing to zero, or by comparing that the between the two objects
  # is more than the given delta:
  assert_almost_equal(first, second, places=7, msg=None, delta=None) 
  
  assert_not_equal(first, second, msg=None)
  assert_not_almost_equal(first, second, places=7, msg=None, delta=None)

  # tests if a function call raises a specified exception when presented 
  # certain parameters:
  assert_raises(nameOfException, functionCalled, *{arguments}, **{keywords}) 

We could also want to write a test that fails but we don't want
properly a failure::

  from nose.plugins.skip import SkipTest 

  try:
    eq_(line[0], 1)
  except Exception:
    raise SkipTest 

Another way is using unittest conventions, that consist of
self.assertX. But the previous form is recommended.

Mock usage
^^^^^^^^^^

`Mock <http://www.voidspace.org.uk/python/mock/>`_ is a python library
for mocks objects.  This allows us to write isolated tests by
simulating services beside using the real ones.

Once we used our mock object, we can make assertions about how it has
been used, like assert if the something function was called one time
with (10,20) parameters::

  from mock import MagicMock
  class TestSomething(object):
    def method(self):
      self.something(10, 20)
    def something(self, a, b):
     pass

  mocked = TestSomething()
  mocked.something = MagicMock()
  mocked.method()
  mocked.something.assert_called_once_with(10, 20)

The above example doesn't prints anything because assert had passed,
but if we call the function below, we will receive an error::

  mocked.something.assert_called_once_with(10, 30)
  > AssertionError: Expected call: mock(10, 30)
  > Actual call: mock(10, 20)

Some other similar functions are ``assert_any_call()``,
``assert_called_once_with()``, ``assert_called_with()`` and
``assert_has_calls()``.

An example about how we could modify whatever we want in a mock object
while keeping it isolated::

  mock = MagicMock()
  mock.__str__.return_value = 'what_i_want'
  str(mock)
  > 'what_i_want'


Side effects returns different values or raises an exception when a
mock is called::

  mock = MagicMock(side_effect=[3, 2, 1])
  mock()
  > 3
  mock()
  > 2
  mock()
  > 1

Decorators
^^^^^^^^^^

We can use ``@patch`` if we want to patch with a Mock. This way the
mock will be created and passed into the test method ::

  class Test(object):
    @mock.patch('package.module.ClassName')
    def test_something(self, MockClass):
      assert_true(package.module.ClassName is MockClass)

It is possible to indicate which tests we want to run. ``[NOSE_ATTR]``
sets to test only the tests that have some specific attribute
specified by ``@attr``::

  from nose.plugins.attrib import attr
  @attr(integration='postgres')
  def test_something(self):
    assert True
  
Code readability
^^^^^^^^^^^^^^^^

Some comments using characters can be used to improve the code
readability::

  #============================================================================
  class TestClass(object):
      """Test a dummy class."""
  
      #------------------------------------------------------------------------
      def test_something(self):
          """A brief description about this test."""
      
          pass

...............

Old instructions (What is important about it?)

* We must either provide for a postgreql account with name and
  password that matches the config file or edit the test config file
  to provide an appropriate test account and password. That file is
  socorro/unittest/config/commonconfig.py. If you add a new test
  config file that needs database access, you should import the
  details from commonconfig, as exemplified in the existing config
  files.
* We must provide a a database appropriate for the test user
  (default: test. That database must support PLPGSQL. As the owner of
  the test database, while connected to that database, invoke ``CREATE
  LANGUAGE PLPGSQL;``

* What is red?

  Short for ``redo`` or ``do it again``.  There is a bash shell file
  called ``socorro/unittest/red`` which may sourced to provide a bash
  function called ``red`` that simplifies watching test logfiles in a
  separate terminal window. In that window, cd to the unittest
  sub-directory of interest, then source the file: . ../red, then call
  ``red``. The effect is to clear the screen, then tail -F the logfile
  associated with tests in that directory. You may chant red --help to
  be reminded.

  The red file also provides a function noseErrors which simplifies
  the examination of nosetests output. Chant noseErrors --help for a
  brief summary.

