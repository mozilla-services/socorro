.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: deployment

.. _deployment-chapter:

Deployment
==========

Introduction
------------

Below are general deployment instructions for installations of Socorro.

Outage Page
-----------
if the system is to be taken down for maintenance, these steps will
show users an outage page during the maintenance period

* backup webapp-php/index.php
* You can copy webapp-php/docs/outage.php over
  webapp-php/index.php and all traffic will be served this outage
  message.
* Do work
* copy backup over webapp-php/index.php

**add other task instructions here**
