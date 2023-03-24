=========================================
Socorro: Mozilla crash ingestion pipeline
=========================================

Socorro is a Mozilla-centric crash ingestion pipeline and analysis tools for
crash reports using the `Breakpad libraries
<http://code.google.com/p/google-breakpad/>`_.

* Free software: Mozilla Public License version 2.0
* Community Participation Guidelines `Guidelines <https://github.com/mozilla-services/socorro/blob/main/CODE_OF_CONDUCT.md>`_
* Chat: `#crashreporting matrix channel <https://chat.mozilla.org/#/room/#crashreporting:mozilla.org>`__
* Socorro (processor/webapp/cron jobs)

  * Code: https://github.com/mozilla-services/socorro/
  * Documentation: https://socorro.readthedocs.io/
  * Bugs: `Report a bug <https://bugzilla.mozilla.org/enter_bug.cgi?format=__standard__&product=Socorro&component=General>`_

* Antenna (collector)

  * Code: https://github.com/mozilla-services/antenna/
  * Documentation: https://antenna.readthedocs.io/
  * Bugs: `Report an Antenna bug <https://bugzilla.mozilla.org/enter_bug.cgi?format=__standard__&product=Socorro&component=Antenna>`_


.. Note::

   This is a very Mozilla-centric product. We do not currently have the
   capacity to support non-Mozilla uses.


Code of Conduct
===============

This project and repository is governed by Mozilla's code of conduct and
etiquette guidelines. For more details please see the `CODE_OF_CONDUCT.md file
<https://github.com/mozilla-services/socorro/blob/main/CODE_OF_CONDUCT.md>`_.


Documentation
=============

Documentation for setting up Socorro, configuration, specifications,
development, and other related things are at
`<https://socorro.readthedocs.io/>`_.


Releases
========

We use continuous development and we release often. See our list of releases
for what changes were deployed to production when:

https://github.com/mozilla-services/socorro/tags


Support
=======

Note: This is a Mozilla-specific product. We do not currently have the capacity
to support external users.

If you are looking to use Socorro for your product, maybe you want to consider
this non-exhaustive list of alternatives:

* run your own: `electron/mini-breakpad-server
  <https://github.com/electron/mini-breakpad-server>`_
* run your own: `wk8/sentry_breakpad <https://github.com/wk8/sentry_breakpad>`_
* hosted/on-premise: `Backtrace <https://backtrace.io/>`_, `BugSplat <https://bugsplat.com/>`_
