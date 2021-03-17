===============
Versions/Builds
===============

Summary
=======

The webapp maintains version/build information for Firefox.

.. graphviz::

   digraph G {
     rankdir=LR;
     splines=lines;

     archivescraper [shape=rect, label="archivescraper"];
     model [shape=box3d, label="crashstats_productversion"];
     betaversionrule [shape=rect, label="BetaVersionRule"];

     archivescraper -> model [label="produces"];
     model -> betaversionrule [label="uses"];
   }


Tables
======

The data is stored in the ``crashstats.ProductVersion`` Django model. This is the
``crashstats_productversion`` table in PostgreSQL.


Where the data comes from
=========================

Data can get in the table in two ways:

1. the ``archivescraper`` Django command scrapes archive.mozilla.org
   data every hour and adds new things to the table

2. the Django admin page lets administrators add new data and edit existing
   data when there are problems


What uses this data
===================

Incoming crash reports for Firefox have a ``Version`` field. There are some
cases where the value is "a lie". In these cases, the processor's
``BetaVersionRule`` will look up the (product, channel, build id) in the
``crashstats_productversion`` table to find the actual version.


About archive.mozilla.org
=========================

Every time a build is created, the binaries and metadata files are published
at:

https://archive.mozilla.org/pub/

Rough directory structure::

  pub/
    firefox/         Firefox builds
      candidates/    beta, rc, release, and esr builds
      nightly/       nightly builds

    devedition/      DevEdition (aka Firefox aurora)
      candidates/    beta builds for Firefox b1 and b2


In the ``candidates/`` subdirectories are build directories like ``build1/``.
Each of those is a release candidate for that version and the last one is
the final.

For example, here's the direcotry for Firefox 64.0b4:

https://archive.mozilla.org/pub/firefox/candidates/64.0b4-candidates/

In it are two build directories: ``build1/`` and ``build2/``. The first is
64.0b4rc1 and was not released to anyone. The second is 64.0b4rc2, but since
it's the last build in that series, it was released as 64.0b4.

Here's the build file for that for linux-i686 in en-US:

https://archive.mozilla.org/pub/firefox/candidates/64.0b4-candidates/build2/linux-i686/en-US/firefox-64.0b4.json

Note how the directory name has "64.0b4", but the ``moz_app_version`` is set to
"64.0".

With recent builds, there's an additional ``buildhub.json`` file:

https://archive.mozilla.org/pub/firefox/candidates/64.0b4-candidates/build1/linux-i686/en-US/buildhub.json

That includes similar information, but is built to be ingested in Buildhub.

Things to know:

1. In a given product, different platforms can have different build ids for
   a version. For example, 54.0b5 has build id 20170504103226 for Windows
   and Mac builds and 20170504173217 for Linux builds.

2. Firefox beta 1 and beta 2 are released in the DevEdition product in the
   aurora channel. That's been happening since Firefox 55.

3. ``https://archive.mozilla.org/pub/*/candidates/`` is periodically purged of
   old data.  For example, at the time of this writing, there's a ton of stuff
   that's missing between Firefox 40 and 49. The builds are still in
   ``/releases/``, but that doesn't include the ``JSON`` files with build
   information.

   Socorro has dumps of the old ``product_versions`` table with the older
   product/build information in Google Drive.
