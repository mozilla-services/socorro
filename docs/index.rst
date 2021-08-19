==================================
Socorro - Crash ingestion pipeline
==================================

Socorro is crash ingestion pipeline consisting of services for collecting,
processing, and analyzing crash data. It is used by Mozilla. Mozilla's crash
analysis tool is hosted at `<https://crash-stats.mozilla.org/>`_.

* Free software: Mozilla Public License version 2.0
* Socorro (processor/webapp/cron jobs)

  * Code: https://github.com/mozilla-services/socorro/
  * Documentation: https://socorro.readthedocs.io/
  * User documentation: https://crash-stats.mozilla.org/documentation/
  * Bugs: `Report a Socorro bug <https://bugzilla.mozilla.org/enter_bug.cgi?format=__standard__&product=Socorro&component=General>`_

* Antenna (collector)

  * Code: https://github.com/mozilla-services/antenna/
  * Documentation: https://antenna.readthedocs.io/
  * Bugs: `Report an Antenna bug <https://bugzilla.mozilla.org/enter_bug.cgi?format=__standard__&product=Socorro&component=Antenna>`_

* Mailing list: https://lists.mozilla.org/listinfo/tools-socorro
* Chat: `#breakpad:mozilla.org <https://riot.im/app/#/room/#breakpad:mozilla.org>`_


.. Note::

   This is a very Mozilla-specific product. We do not currently have the
   capacity to support non-Mozilla uses.


.. toctree::
   :caption: For Socorro/Crash Stats Users
   :includehidden:
   :maxdepth: 1

   overview
   whatsnew
   signaturegeneration
   reprocessing
   products
   telemetry_socorro_crash
   correlations
   annotations


Crash Stats site documentation covering API docs, getting access to memory dumps,
and Supersearch is located at `<https://crash-stats.mozilla.org/documentation/>`_.


.. toctree::
   :caption: For Socorro Developers and Ops
   :includehidden:
   :maxdepth: 1

   localdevenvironment
   contributing
   service/index
   flows/index
   stackwalk
   crashstorage
   crashqueue
   adr_log
   tests/system_checklist


.. toctree::
   :caption: Specifications and Resources
   :includehidden:
   :maxdepth: 1

   spec_crashreport
   schemas
