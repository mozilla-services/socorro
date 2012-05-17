.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: filesystem

.. _filesystem-chapter:


File System
===========

Socorro uses two similar file system storage schemes in two distinct
places within the system. Raw crash dumps from the field use a system
called :ref:`jsondumpstorage-chapter` while at the other end, processed dumps use the
:ref:`processeddumpstorage-chapter` scheme.
