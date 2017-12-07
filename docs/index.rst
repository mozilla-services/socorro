==================================
Socorro - Crash ingestion pipeline
==================================

Socorro is a set of components for collecting, processing and reporting on
crashes. It is used by Mozilla for tracking crashes of Mozilla products.

Mozilla's crash analysis tool is hosted at
`<https://crash-stats.mozilla.com/>`_.

The components which make up Socorro are:

* Collector - collects breakpad minidump crashes which come in over HTTP POST

  `Antenna <https://antenna.readthedocs.io/>`_ now collects crashes for Socorro.

* Processor - turn breakpad minidump crashes into stack traces and other info
* Web UI for analysis aka crash-stats - Django-based web app for visualizing
  crash data

Socorro is available from source in a git repository at
`<https://github.com/mozilla-services/socorro/>`_.

* Free software: Mozilla Public License version 2.0
* Code:

  * Antenna: https://github.com/mozilla-services/antenna
  * Socorro: https://github.com/mozilla-services/socorro

* Documentation: https://antenna.readthedocs.io/


Contents
========

.. toctree::
   :numbered:
   :includehidden:
   :maxdepth: 2
   :glob:

   gettingstarted
   contributing
   symbols
   architecture/*
   components/*
   services/*
   tests/*
   deploy
   howto
