This is the directory that holds unit tests. 
See the unittesting wiki page: http://code.google.com/p/socorro/wiki/SocorroUnitTests

The layout of this directory is:

unittest       # this directory
 - README.txt  # this file
 - red         # A stupidly simple little bash utility to help with debugging
               # via tail -F of the log file. Chant "red --help" for more
 - testlib     # holds test utility code AND some tests for that code
 - <directory> # One directory here for each (working, not testing) directory
               # in the socorro directory above

Requirements to run unittests:
 nose and nosetests
 Postgresql server
 python 2.4 or greater
 check out https://socorro.googlecode.com/svn/trunk/thirdparty
  - and add .../thirdparty to your PYTHON_PATH

nosetests configuration: You should NOT attempt to pass command line arguments
to nosetests: It leaves them in sys.argv where they confuse the socorro
configuration system. Instead, set environment variables. Chant nosetests --help
Two useful ones:
  NOSE_VERBOSE=x for x in [0,1,2]
   0: Very quiet
   1: one '.' per test as with unittest behavior
   2: per test: Prints a very brief summary and then a status (ok/FAIL/ERROR)
  NOSE_NOCAPTURE=1 
   print statements are not captured but passed to the console.
You can also create $HOME/.noserc or $HOME/nose.cfg, standard .ini format.
for example:
[nosetests]
verbosity=2
nocapture=1

The combination of nosetests and postgresql seems to trigger a problem when
the database hangs because it is waiting for a cursor to finish before another
action can take place: nosetests cannot be easily killed. You will have to
suspend the nosetests process via Ctrl-z and then SIGKILL it: kill -9 . Lesser
kill signals will not be effective. Doing this will leave the database in a dirty
state, which is why setup code in most test files first cleans the database and
then rebuilds it.

Using nosetests. Documentation is here:
 http://somethingaboutorange.com/mrl/projects/nose/0.11.1/usage.html
 (and poke around in the vicinity if needed)

How to run unittests:
  All the unit tests:
    cd to this directory
    set NOSE_??? envariables or add $HOME/.noserc if you wish
    chant nosetests > testOutputFilename 2>&1 # to retain output
    chant nosetests # to observe output directly
    NOTE: after sourcing the file 'red' in this directory, you can use the shell
    function noseErrors: noseErrors [options] testOutputFilename
  All the unit tests for a particular directory
    cd to unittests/something
    ... and continue as above
 Any particular unittest
  cd to unittests/something
    probably: chant nosetests testSomething:TestSomething.testIndividual
     - most tests live in a class named like the test filename but CamelCapitalized
    occasionally: chant nosetests testSomething:testIndividualName
     - some tests live directly in the test file
    rarely: chante nosetests testSomething:TestSomeClass.testIndividualName
     - a very few tests live in a class that is not named for the test filename

Expect two errors from unittest/lib/testJsonDumpStorageGid.py unless you are running as root:

testCopyFromGid (socorro.unittest.lib.testJsonDumpStorageGid.TestJsonDumpStorageGid) ... ERROR
testNewEntryGid (socorro.unittest.lib.testJsonDumpStorageGid.TestJsonDumpStorageGid) ... ERROR
...
======================================================================
ERROR: testCopyFromGid (socorro.unittest.lib.testJsonDumpStorageGid.TestJsonDumpStorageGid)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/griswolf/work/Mozilla/griswolf-work/socorro/unittest/lib/testJsonDumpStorageGid.py", line 13, in setUp
    assert 'root' == pwd.getpwuid(os.geteuid())[0], "You must run this test as root (don't forget root's PYTHONPATH)"
AssertionError: You must run this test as root (don't forget root's PYTHONPATH)

======================================================================
ERROR: testNewEntryGid (socorro.unittest.lib.testJsonDumpStorageGid.TestJsonDumpStorageGid)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/griswolf/work/Mozilla/griswolf-work/socorro/unittest/lib/testJsonDumpStorageGid.py", line 13, in setUp
    assert 'root' == pwd.getpwuid(os.geteuid())[0], "You must run this test as root (don't forget root's PYTHONPATH)"
AssertionError: You must run this test as root (don't forget root's PYTHONPATH)

----------------------------------------------------------------------
