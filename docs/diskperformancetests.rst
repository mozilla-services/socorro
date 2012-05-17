.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: diskperformancetests

.. _diskperformancetests-chapter:


Disk Performance Tests
======================

Introduction
------------

Any DBMS for a database which is larger than memory can be no faster
than disk speed. This document outlines a series of tests for testing
disk speed to determine if you have an issue. Written originally by
PostgreSQL Experts Inc. for Mozilla.

Running Tests
-------------

Note: all of the below require you to have plenty of disk space
available. And their figures are only reliable if nothing else is
running on the system.


**Simplest Test: The DD Test**

This test measures the most basic single-threaded disk access: a large
sequential write, followed by a large sequential read. It is relevant
to database performance because it gives you a maximum speed for
sequential scans for large tables. Real table scans are generally
about 30% of this maximum.

dd is a Unix command line utility which simply writes to a block
device. We use it for this 3-step test. The other thing you need to
know for this test is your RAM size.

1. We create a large file which is 2x the size of RAM, and synch it to
   disk. This makes sure that we get the real sustained write rate,
   because caching can have little effect. Since there are 125000 blocks
   per GB (8k blocksize is used because it's what Postgres uses), if we
   had 8GB of RAM, we would run the following::

        time sh -c "dd if=/dev/zero of=ddfile bs=8k count=1000000 && sync"

   dd will report a time and write rate to us, and "time" will report
   a larger time. The time and rate reported by dd represents the rate
   without any lag or synch time; divide the data size by the time
   reported by "time" for synchronous file writing rate.

2. Next we want to write another large file, this one the size of RAM,
   in order to flush out the FS cache so that we can read directly
   from disk later.::

        dd if=/dec/zero of=ddfile2 bs=8K count=500000

3. Now, we want to read the first file back. Since the FS cache is
   full from the second file, this should be 100% disk access::

        time dd if=ddfile of=/dev/null bs=8k

This time, "time" and dd will be very close together; any difference
will be strictly storage lag time.


Bonnie++
--------

Bonnie++ is a more sophisticated set of tests which tests random reads
and writes, as well as seeks, and file creation and deletion
operations. For a modern system, you want to use the last version,
1.95, downloaded from http://www.coker.com.au/bonnie++/experimental/
This final version of bonnie++ supports concurrency and measures lag
time. However, it is not available in package form in most OSes, so
you'll have to compile it using g++.

Again, for Mozilla we want to test performance for a database which is
larger than RAM, since that's what we have. Therefore, we're going to
run a concurrent Bonnie++ test where the total size of the files is
about 150% of RAM, forcing the use of disk. We're also going to run 8
threads to simulate concurrent file access. Our command line for a
machine with 16GB RAM is::

 bonnie++ -d /path/to/storage -c 8 -r 16000 -n 100

The results we get back look something like this::

 Version  1.95       ------Sequential Output------ --Sequential Input- --Random-
 Concurrency   8     -Per Chr- --Block-- -Rewrite- -Per Chr- --Block-- --Seeks--
 Machine        Size K/sec %CP K/sec %CP K/sec %CP K/sec %CP K/sec %CP /sec %CP
 tm-breakpad0 32000M   757  99 71323  16 30594   5  2192  99 57555   4 262.5  13
 Latency             15462us    6918ms    4933ms   11096us     706ms 241ms
 Version  1.95       ------Sequential Create------ --------Random Create--------
 tm-breakpad01-maste -Create-- --Read--- -Delete-- -Create-- --Read--- -Delete--
               files  /sec %CP  /sec %CP  /sec %CP  /sec %CP  /sec %CP /sec %CP
                 100 44410  75 +++++ +++ 72407  81 45787  77 +++++ +++ 63167  72
 Latency              9957us     477us     533us     649us      93us 552us

So, the interesting parts of this are:

Sequential Output: Block: this is sequential writes like dd does. It's
70MB/s.

Sequential Input: Block: this is sequential reads from disk. It's
57MB/s.

Sequential Output: Rewrite: is reading, then writing, a file which has
been flushed to disk. This rate will be lower than either of the
above, and is at 30MB/s.

Random: Seeks: this is how many individual blocks Bonnie can seek to
per second; it's a fast 262.

Latency: this is the full round-trip lag time for the mentioned
operation. On this platform, these times are catastrophically bad; 1/4
second round-trip to return a single random block, and 3/4 seconds to
return the start of a large file.

The figures on file creations and deletion are generally less
interesting to databases. The +++++ are for runs that were so fast the
error margin makes the figures meaningless; for better figures,
increase -n.

IOZone
------

Now, if you don't think Bonnie++ told you enough, you'll want to run
Iozone. Iozone is a benchmark mostly know for creating pretty graphs
(http://www.iozone.org/) of filesystem performance with different
file, batch, and block sizes. However, this kind of comprehensize
profiling is completely unnecessary for a DBMS, where we already know
the file access pattern, and can take up to 4 days to run. So do not
run Iozone in automated (-a) mode!

Instead, run a limited test. This test will still take several hours
to run, but will return a more limited set of relevant results. Run
this on a 16GB system with 8 cores, from a directory on the storage
you want to measure::

 iozone -R -i 0 -i 1 -i 2 -i 3 -i 4 -i 5 -i 8 -l 6 -u 6 -r 8k -s 4G -F f1 f2 f3 f4 f5 f6

This runs the following tests: write/read, rewrite/reread,
random-read/write, read-backwards, re-write-record, stride-read,
random mix. It does these tests using 6 concurrent processes, a block
size of 8k (Postgres' block size) for 4G files named f1 to f6. The
aggregate size of the files is 24G, so that they won't all fit in
memory at once.

In theory, the relevance of these tests to database activity is the
following:

write/read: basic sequential writes and reads.

rewrite/reread: writes and reads of frequently accessed tables (in memory)

random-read/write: index access, and writes of individual rows

read-backwards: might be relevant to reverse index scans.

re-write-record: frequently updated row behavior

stride-read: might be relevant to bitmapscan

random mix: general database access average behavior.

The results you get will look like this::

        Children see throughput for  6 initial writers  =  108042.81 KB/sec
        Parent sees throughput for  6 initial writers   =   31770.90 KB/sec
        Min throughput per process                      =   13815.83 KB/sec
        Max throughput per process                      =   35004.07 KB/sec
        Avg throughput per process                      =   18007.13 KB/sec
        Min xfer                                        = 1655408.00 KB

And so on through all the tests. These results are pretty
self-explanatory, except that I have no idea what the difference
between "Children see" and "Parent sees" means. Iozone documentation
is next-to-nonexistant.

Note: IOZone appears to have several bugs, and places where its
documentation and actual features don't match. Particularly, it
appears to have locking issues in concurrent access mode for some
writing activity so that concurrency throughput may be lower than
actual.
