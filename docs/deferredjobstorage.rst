.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: deferredjobstorage

.. _deferredjobstorage-chapter:


Deferred Job Storage
====================

Deferred storage is where the JSON/dump pairs are saved if they've
been filtered out by :ref:`collector-chapter` throttling. The location of the
deferred job storage is determined by the configuration parameter
deferredStorageRoot found in the :ref:`commonconfig-chapter`.

JSON/dump pairs that are saved in deferred storage are not likely to
ever be processed further. They are held for a configurable number of
days until deleted by :ref:`deferredcleanup-chapter`.

Occasionally, a developer will request a report via :ref:`reporter-chapter` on
a job that was saved in deferred storage. :ref:`monitor-chapter` will look for
the job in deferred storage if it cannot find it in standard storage.

For more information on the storage technique, see :ref:`filesystem-chapter`
