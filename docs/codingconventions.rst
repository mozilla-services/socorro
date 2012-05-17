.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: codingconventions

.. _codingconventions-chapter:


Coding Conventions
==================

Introduction
------------

The following coding conventions are designed to ensure that the
Socorro code is easy to read, hack, test, and deploy.

Style Guide
-----------

* Python should follow PEP 8 with 4 space indents
* PHP code follows the PEAR coding standard
* JavaScript is indented by four spaces
* :ref:`unittesting-chapter` is strongly encouraged

Review
------

New checkins that are non-trivial should be reviewed by one of the
core hackers. The commit message should indicate the reviewer and the
issue number if applicable.

Testing
-------

Any features that are only available to admins should be tested to
ensure that only non-admin users to not have access.

Before checking in changes to the socorro python code, be sure to run
the unit tests.
