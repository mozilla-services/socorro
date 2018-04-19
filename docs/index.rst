==================================
Socorro - Crash ingestion pipeline
==================================

Socorro is a set of components for collecting, processing, and analyzing crash
data. It is used by Mozilla for analyzing crash data for Mozilla products.
Mozilla's crash analysis tool is hosted at
`<https://crash-stats.mozilla.com/>`_.


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

   overview
   gettingstarted
   contributing
   signaturegeneration
   stackwalker
   topcrashersbysignature
   schemas
   service/*
   crashstorage/*
   tests/*
   socorro_app
   deploy
   howto
