==================================
Socorro - Crash ingestion pipeline
==================================

Overview
========

Socorro is a set of components for collecting, processing, and analyzing crash
data. It is used by Mozilla for analyzing crash data for Mozilla products.
Mozilla's crash analysis tool is hosted at
`<https://crash-stats.mozilla.com/>`_.

The components which make up Socorro are:

* Collector: Collects incoming crash reports via HTTP POST. The collector we
  currently use is `Antenna <https://antenna.readthedocs.io/>`_ now collects
  crashes for Socorro.
* Processor: Turns breakpad minidump crashes into stack traces and other info.
* Webapp/Crash Stats: Web user interface for analyzing crash data.
* Crontabber: Runs hourly/daily/weekly tasks for analyzing and processing data.

Data that's processed gets stored in several crash storage destinations.

Project info
============

:Free software: Mozilla Public License version 2.0
:Code: https://github.com/mozilla-services/socorro/ and https://github.com/mozilla-services/antenna
:Documentation: https://socorro.readthedocs.io/
:Mailing list: https://lists.mozilla.org/listinfo/tools-socorro
:IRC: `<irc://irc.mozilla.org/breakpad>`_
:Bugs: https://bugzilla.mozilla.org/enter_bug.cgi?format=__standard__&product=Socorro


Contents
========

.. toctree::
   :numbered:
   :includehidden:
   :maxdepth: 1
   :glob:

   gettingstarted
   contributing
   signaturegeneration
   topcrashersbysignature
   service/*
   crashstorage/*
   tests/*
   socorro_app
   deploy
   howto
