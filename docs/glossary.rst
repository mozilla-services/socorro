.. index:: glossary

.. _glossary-chapter:


Glossary
========

**Build**: a date encoding used to identify when a client was compiled.
(submission metadata)

**Crash Report Details Page** - A crash stats page displaying all known
details of a crash

**Crash Dump/Metadata pair** - shorthand for The pair of Raw Crash Dump
and corresponding Raw Crash Metadata

:ref:`deferredjobstorage-chapter`: a file system location where Crash Dump/Metadata
pair are kept without being processed.

**Dump File**: See Raw Crash Dump, don't use this term it makes me giggle

**Job**: a job queue item for a Raw Crash Dump that needs to be processed

:ref:`jsondumpstorage-chapter`: the Python module that implements
:ref:`filesystem-chapter`

**Materialized view**: the tables in the database containing the data for
used in statistical analysis. Including: [[MeanTimeBeforeFailure]],
:ref:`topcrashersbysignature-chapter`, :ref:`topcrashersbyurl-chapter`. The "Trend Reports" from the
:ref:`ui-chapter` display information from these tables.

**Minidump**: see 'raw crash dump'

**Minidump_stackwalk**: an application from the Breakpad project that
takes a raw dump file, marries it with symbols and produces output
usable by developers. This application is invoked by
:ref:`processor-chapter`.

**Monitor**: the Socorro application in charge of queuing jobs. See
:ref:`monitor-chapter`

**OOID**: A crash report ID. Originally a 32bit value, the original legacy
system stored it in the database as a hexidecimal text form. Each
crash is assigned an OOID by the :ref:`collector-chapter` when the crash is
recieved.

**Platform**: the OS that a client runs on. This term has been
historically a point of confusion and it is preferred that the term OS
or Client OS be used instead.

:ref:`processeddumpstorage-chapter`: the disk location where the output files of the
minidump_stackwalk program are stored. The actual files are stored
with a .jsonz extension.

**Processor**: the Socorro application in charge of applying
minidump_stackwalk to queued jobs. See :ref:`processor-chapter`

**Raw Crash Dump, Raw Dump**: the data sent from a client to Socorro
containing the state of the application at the time of failure. It is
paired with a Raw Crash Metadata file.

**Raw Crash Metadata** - the metadata sent from a client to Socorro to
describe the Raw Crash. It is saved in JSON format, not to be confused
with a Cooked Crash Dump.

**Raw JSON file**: See Crash Dump Metadata... a file in the JSON format
containing metadata about a 'dump file'. Saved with a '.json' suffix.

**Release**: a categorization of an application's product name and
version. The categories are: "major", "milestone", or "development".
Within the database, an enum called ReleaseEnum? represents these
categories.

**Reporter**: another name for the :ref:`ui-chapter`

**Skip List**: lists of signature regular expressions used in generating a
crash's overall signature in the :ref:`processor-chapter`. see
:ref:`signaturegeneration-chapter`

:ref:`standardjobstorage-chapter`: a file system location where JSON/dump pairs are
kept for processing

**Throttling**: statistically, we don't have to save every single crash.
This option of the :ref:`collector-chapter` configuration allows us to
selectively throw away dumps.

**Trend Reports**: the pages in the :ref:`ui-chapter` that display the data from
the materialized views.

**UUID**: a univeral unique identifier. Term is being deprecated in favor
of OOID.

**Web head**: a machine that runs :ref:`collector-chapter`


.. toctree::
   :maxdepth: 2

   deferredjobstorage
   jsondumpstorage
   processeddumpstorage
   standardjobstorage
   topcrashersbyurl
   topcrashersbysignature
   signaturegeneration
   crashmover
   collector
   reporter
   monitor
   filesystem
   deferredcleanup
