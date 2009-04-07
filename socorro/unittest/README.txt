This is the directory that holds unit tests. 
See the unittesting wiki page: http://code.google.com/p/socorro/wiki/SocorroUnitTests

The layout of this directory is:

unittest       # this directory
 - README.txt  # this file
 - red         # A stupidly simple little bash utility to help with debugging
               # via tail -F of the log file
 - testlib     # holds test utility code AND some tests for that code
 - <directory> # One directory here for each (working, not testing) directory
               # in the socorro directory above

Requirements to run unittests:
 nose and nosetests
 Postgresql server
 python 2.4 or greater

nosetests configuration: You should NOT attempt to pass command line arguments
to nosetests: It leaves them in sys.argv where they confuse the socorro
configuration system. Instead, set environment variables. Chant nosetests --help
Two useful ones:
  NOSE_VERBOSE=x for x in [0,1,2]
   0: Very quiet
   1: one '.' per test as with unittest behavior
   2: per test: Prints a very brief summary and then a status (ok/FAIL/ERROR)
  NOSE_NOCAPTURE=1 
   print statements are not captured, but passed to the console.

The combination of nosetests and postgresql seems to trigger a problem when
the database hangs because it is waiting for a cursor to finish before another
action can take place: nosetests cannot be easily killed. You will have to
suspend the nosetests process via Ctrl-z and then SIGKILL it: kill -9 . Lesser
kill signals will not be effective. Doing this will leave the database in a dirty
state, which is why setup code in most test files first cleans the database and
then rebuilds it.

How to run unittests:
  cd to this directory
  set NOSE_??? envariables if you wish
  chant nosetests
  observe the results. Expect two errors unless you are running as root:

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
