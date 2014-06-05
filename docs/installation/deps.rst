.. index:: deps

.. _dependencies-chapter:

Installing dependencies
=======================
Requirements
------------

.. sidebar:: Breakpad client and symbols

   Socorro aggregates and reports on Breakpad crashes.
   Read more about `getting started with Breakpad <http://code.google.com/p/google-breakpad/wiki/GettingStartedWithBreakpad>`_.

   You will need to `produce symbols for your application <http://code.google.com/p/google-breakpad/wiki/LinuxStarterGuide#Producing_symbols_for_your_application>`_ and make these files available to Socorro.

* Mac OS X or Linux (Ubuntu/RHEL)
* PostgreSQL 9.3
* RabbitMQ 3.1
* Python 2.6
* C++ compiler (GCC 4.6 or greater)
* Subversion
* Git
* PostrgreSQL and Python dev libraries (for psycopg2)

Virtual Machine using Vagrant
-----------------------------

You can quickly spin up a CentOS VM using Vagrant:

:ref:`vagrant-chapter`

On your own machine
-------------------

Mozilla uses and supports Red Hat Enterprise Linux for
https://crash-stats.mozilla.com (and clones such as CentOS) but we provide
installation instructions for setting up development environments on
Ubuntu and Mac OS X as well.

:ref:`rhel-chapter`

:ref:`ubuntu-chapter`

:ref:`mac-chapter`
