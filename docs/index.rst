.. Socorro documentation master file, created by
   sphinx-quickstart on Wed Sep 21 14:59:08 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root ``toctree`` directive.

Socorro
=======
Socorro is a set of components for collecting, processing and reporting on crashes. It is used by Mozilla for tracking crashes of Firefox, B2G, Thunderbird and other projects. The production Mozilla install is public and hosted at https://crash-stats.mozilla.com/

The components which make up Socorro are:

* Collector - collects breakpad minidump crashes which come in over HTTP POST
* Processor - turn breakpad minidump crashes into stack traces and other info
* Middleware - provide HTTP REST interface for JSON reports and real-time data
* Web UI aka crash-stats - django-based web app for visualizing crash data

For help with installation, start with :ref:`intro-chapter`.

We welcome contributions!

* Start here to contribute to documentation: :ref:`writingdocs-chapter`.
* Start here to contribute code: :ref:`newdeveloperguide-chapter`.

See http://wiki.mozilla.org/Breakpad for up-to-date information about development team activity and our meetings.

This documentation is `available on readthedocs <http://socorro.readthedocs.org>`_. The source and current development activity is `available on Github <https://github.com/mozilla/socorro/tree/master>`_.

The Socorro development mailing list is https://lists.mozilla.org/listinfo/tools-socorro


Contents:

.. toctree::
   :maxdepth: 2

   installation/index
   installation/deps
   installation/download
   installation/install-binary
   installation/install-src-dev
   installation/install-src-prod
   installation/systemtest
   installation/setup-socorro
   installation/troubleshoot
   webapp
   api/index
   crontabber
   elasticsearch
   throttling
   contributing
   database
   generic_app
   writingdocs
   glossary/index


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
