.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: dumpingdumptables

.. _dumpingdumptables-chapter:


Dumping Dump Tables
===================

A work item that came out of the Socorro Postgres work week is to dump the dump tables and store cooked dumps as gzipped files.
Drop dumps table

convert each dumps table row to a compressed file on disk

Bugzilla
--------

https://bugzilla.mozilla.org/show_bug.cgi?id=484032

Library support
---------------

'done' as of 2009-05-07 in socorro.lib.dmpStorage (Coding, testing is done; integration testing is done, 'go live' is today)
Socorro UI

/report/index/{uuid}

* Will stop using the dumps table.
* Will start using gzipped files
   * Will use the report uuid to locate the dump on a file system
   * Will use apache mod-rewrite to serve the actual file. The rewrite
     rule is based on the uuid, and is 'simple':
     AABBCCDDEEFFGGHHIIJJKKLLM2090308.jsonz => AA/BB/AABBCCDDEEFFGGHHIIJJKKLLM2090308.jsonz
   * report/index will include a link to JSON dump

      link rel='alternate' type='application/json' href='/reporter/dumps/cdaa07ae-475b-11dd-8dfa-001cc45a2ce4.jsonz'

Dump file format
----------------

* Will be gzip compressed JSON encoded cooked dump files
* Partial JSON file
* Full JSONZ file

On Disk Location
----------------

    application.conf dumpPath Example for kahn $config'dumpPath'? = '/mnt/socorro_dumps/named';

In the dumps directory we will have an .htaccess file::

  AddType "application/json; charset=UTF-8" jsonz
  AddEncoding gzip jsonz

Webhead will serve these files as::

  Content-Type: application/json; charset=utf-8
  Content-Encoding: gzip

**Note:* You'd expect the dump files to be named json.gz, but this is
broken in Safari. By setting HTTP headers and naming the file jsonz,
an unknown file extension, this works across browsers.

Socorro UI
----------

* Existing URL won't change.
* Second JSON request back to server will load jsonz file

Example:

* http://crash-stats.mozilla.com/report/index/d92ebf79-9858-450d-9868-0fe042090211
* http://crash-stats.mozilla.com/dump/d92ebf79-9858-450d-9868-0fe042090211.jsonz

mod rewrite rules will match /dump/.jsonz and change them to access a file share.

Future Enhancement
------------------

A future enhancement if we find webheads are high CPU would be to move
populating the report/index page to client side.

Test Page
---------

http://people.mozilla.org/~aking/Socorro/dumpingDump/json-test.html -
Uses browser to decompress a gzip compressed JSON file during an AJAX
request, pulls it apart and appends to the page.

Test file made with gzip dump.json
