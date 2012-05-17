.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: generalarchitecture

.. _generalarchitecture-chapter:

General architecture of Socorro
===============================

If you clone our `git repository <https://github.com/mozilla/socorro>`_, you
will find the following folders. Here is what each of them contains:

+--------------+-------------------------------------------------------------+
| Folder       | Description                                                 |
+==============+=============================================================+
| analysis/    | Contains metrics jobs such as mapreduce. Will be moved.     |
+--------------+-------------------------------------------------------------+
| config/      | Contains the Apache configuration for the different parts   |
|              | of the Socorro application.                                 |
+--------------+-------------------------------------------------------------+
| docs/        | Documentation of the Socorro project (the one you are       |
|              | reading right now).                                         |
+--------------+-------------------------------------------------------------+
| scripts/     | Scripts for launching the different parts of the Socorro    |
|              | application.                                                |
+--------------+-------------------------------------------------------------+
| socorro/     | Core code of the Socorro project.                           |
+--------------+-------------------------------------------------------------+
| sql/         | SQL scripts related to our PostgreSQL database. Contains    |
|              | schemas and update queries.                                 |
+--------------+-------------------------------------------------------------+
| thirparty/   | External libraries used by Socorro.                         |
+--------------+-------------------------------------------------------------+
| tools/       | External tools used by Socorro.                             |
+--------------+-------------------------------------------------------------+
| webapp-php/  | Front-end PHP application (also called UI). See             |
|              | :ref:`ui-chapter`.                                          |
+--------------+-------------------------------------------------------------+

Socorro submodules
------------------

The core code module of Socorro, called ``socorro``, contains a lot of code.
Here are descriptions of every submodule in there:

+-------------------+---------------------------------------------------------------+
| Module            | Description                                                   |
+===================+===============================================================+
| collector         | All code related to collectors.                               |
+-------------------+---------------------------------------------------------------+
| cron              | All cron jobs running around Socorro.                         |
+-------------------+---------------------------------------------------------------+
| database          | PostgreSQL related code.                                      |
+-------------------+---------------------------------------------------------------+
| deferredcleanup   | Osolete.                                                      |
+-------------------+---------------------------------------------------------------+
| external          | Here are APIs related to external resources like databases.   |
+-------------------+---------------------------------------------------------------+
| integrationtest   | Osolete.                                                      |
+-------------------+---------------------------------------------------------------+
| lib               | Different libraries used all over Socorro’s code.             |
+-------------------+---------------------------------------------------------------+
| middleware        | New-style middleware services place.                          |
+-------------------+---------------------------------------------------------------+
| monitor           | All code related to monitors.                                 |
+-------------------+---------------------------------------------------------------+
| othertests        | Some other tests?                                             |
+-------------------+---------------------------------------------------------------+
| services          | Old-style middleware services place.                          |
+-------------------+---------------------------------------------------------------+
| storage           | HBase related code.                                           |
+-------------------+---------------------------------------------------------------+
| unittest          | All our unit tests are here.                                  |
+-------------------+---------------------------------------------------------------+
| webapi            | Contains a few tools used by web-based services.              |
+-------------------+---------------------------------------------------------------+
