.. index:: requirements

.. _requirements-chapter:


Requirements
============

Introduction
------------

The requirement below are broken down functionally in order of
dependence. You don't necessarily have to run these on the same
physical machine.

Database
--------

* Recent Linux distro (such as Red Hat Enterprise Linux Server release 5.2)
* PostgreSQL 9.0.4

Socorro Server
--------------

* Socorro Database
* minidump_stackwalk
* Python 2.6 or higher
   * SimpleJson? package
   * psycopg2 package

Socorro UI
----------

* Socorro Database
* Apache 2.x with mod_rewrite support
* PHP 5.x
    * optionally with memcache support
* Memcached (optional)
* Python 2.6 or higher
* cron or similar system
