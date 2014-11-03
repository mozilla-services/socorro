.. index:: package

.. _package-chapter:


Package
=======

The applications that run the :ref:`server-chapter` are written in Python. The
source code for these packages is collected into a single package.

There is no current installation script for this package. It just must
be available somewhere on the PYTHONPATH.

Package Layout
--------------

* ``.../scripts`` : for socorro applications
* ``.../scripts/config`` : configuration for socorro applications
* ``.../socorro`` : python package root
* ``.../socorro/collector`` : modules used by the collector application
* ``.../socorro/cron`` : modules used by various applications intended to run by cron
* ``.../socorro/database`` : modules associated with the relational database
* ``.../socorro/deferredcleanup`` : modules used by the deferred file system cleanup script
* ``.../socorro/integrationtest`` : for future use
* ``.../socorro/lib`` : common modules used throughout the system
* ``.../socorro/monitor`` : modules used by the monitor application
* ``.../socorro/processor`` : modules used by the processor application
* ``.../socorro/unittest`` : testing framework modules
