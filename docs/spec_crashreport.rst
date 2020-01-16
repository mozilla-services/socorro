===========================
Specification: Crash report
===========================

This is a specification for the format for submitting crash reports.

.. contents::
   :local:

crash report: v0
================

v0 refers to whatever we had prior to when we moved crash annotations into a
single JSON-encoded field in `bug 1420363
<https://bugzilla.mozilla.org/show_bug.cgi?id=1420363>`_. That work landed in
December 2019 and is in Firefox 73.


Submitting a crash report
-------------------------

Crash reports are submitted by HTTP POST to a URL for a crash ingestion
collector.


Crash report HTTP POST headers
------------------------------

The content type header of the crash report must be ``multipart/form-data``
and specify the multipart/form-data boundary.

The content length of the crash report must be set. The value is the length
of the body.

The ``Content-Encoding`` may be set to ``gzip`` if the HTTP body is gzipped.


Crash report HTTP body
----------------------

The crash report is in the HTTP POST body.

If the ``Content-Encoding`` header is set to ``gzip``, the body must be
gzipped.

The body consists of a series of multipart/form-data fields. Each field is
either an annotation or a binary like a minidump.

.. seealso::

   RFC for multipart/form-data:
      https://tools.ietf.org/html/rfc7578


Annotation fields
~~~~~~~~~~~~~~~~~

1. The ``Content-Displosition`` must be ``form-data``.

2. The ``Content-Disposition`` must specify a ``name``. This is the annotation
   name. It must be in ASCII.

3. The value of this field is the annotation value. It is always a string.

Example::

   Content-Disposition: form-data; name="AddonsShouldHaveBlockedE10s"

   1


Binary fields
~~~~~~~~~~~~~

1. The ``Content-Disposition`` must be ``form-data``.

2. The ``Content-Disposition`` must specify a ``name``. It must be in ASCII.

   Examples of names:

   * ``memory_report``
   * ``upload_file_minidump``
   * ``upload_file_minidump_browser``
   * ``upload_file_minidump_content``
   * ``upload_file_minidump_flash1``
   * ``upload_file_minidump_flash2``

3. The ``Content-Disposition`` may specify a ``filename``.

   Examples of filenames:

   * ``6da3499e-f6ae-22d6-1e1fdac8-16464a16.dmp``

4. The ``Content-Type`` must be ``application/octet-stream``.

5. The value of this field is binary data.

Example::

   Content-Disposition: form-data; name="upload-file-minidump"; filename="6da3499e-f6ae-22d6-1e1fdac8-16464a16.dmp"
   Content-Type: application/octet-stream

   BINARYDATA


Collector response
------------------

Accepted
~~~~~~~~

If the crash report is accepted by the collector, then the collector must
return an HTTP status code of 200 with a body specifying the crash id::

   "CrashID" "=" CRASHID

For example::

   CrashID=bp-d101d046-638f-42e0-902d-bd245c200115


Rejected because of throttling rule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the crash report is rejected by the collector, then the collector must
return an HTTP status code of 200 with a body specifying the rejection rule::

   "Discarded" "=" RULE

For example::

   Discarded=rule_has_hangid_and_browser

Rejection rules are specified in the collector's throttler. They are added and
removed as needed.

Some rejection rules are hard-rejections and the collector will never accept
that crash report.

Some rejection rules are soft-rejections and the collector may accept that
crash report again in the future.

The crash reporter client may submit the crash report again.

.. seealso::

   Code for throttler:
      https://github.com/mozilla-services/antenna/blob/master/antenna/throttler.py


Rejected because it's malformed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the crash report is malformed, then the collector must return an HTTP status
code of 400 with a body specifying the malformed reason::

   "Discarded" "=" REASON

For example::

   Discarded=no_annotations


Non-exhaustive list of reasons the crash report could be malformed:

``no_content_type``
   The crash report HTTP POST has no content type in the HTTP headers.

``wrong_content_type``
  The crash report HTTP POST content type header exists, bug it's not set to
  ``malformed/form-data``.

``no_boundary``
   The content type doesn't include a boundary value, so it can't be parsed as
   ``multipart/form-data``.

``bad_gzip``
   The ``Content-Encoding`` header is set to ``gzip``, but the body isn't in
   gzip format or there's a parsing error.

``no_annotations``
   The crash report has been parsed, but there were no annotations in it.


The crash reporter client shouldn't try to send a malformed crash report again.


Example of crash report HTTP POST
---------------------------------

Example with HTTP headers and body::

   POST /submit HTTP/1.1
   Host: xyz.example.com
   User-Agent: Breakpad/1.0 (Linux)
   Accept: */*
   Content-Length: 1021
   Content-Type: multipart/form-data; boundary=------------------------c4ae5238f12b6c82

   --------------------------c4ae5238f12b6c82
   Content-Disposition: form-data; name="Add-ons"

   ubufox%40ubuntu.com:3.2,%7B972ce4c6-7e08-4474-a285-3208198ce6fd%7D:48.0,loop%40mozilla.org:1.4.3,e10srollout%40mozilla.org:1.0,firefox%40getpocket.com:1.0.4,langpack-en-GB%40firefox.mozilla.org:48.0,langpack-en-ZA%40firefox.mozilla.org:48.0
   --------------------------c4ae5238f12b6c82
   Content-Disposition: form-data; name="AddonsShouldHaveBlockedE10s"

   1
   --------------------------c4ae5238f12b6c82
   Content-Disposition: form-data; name="BuildID"

   20160728203720
   --------------------------c4ae5238f12b6c82
   Content-Disposition: form-data; name="upload_file_minidump"; filename="6da3499e-f6ae-22d6-1e1fdac8-16464a16.dmp"
   Content-Type: application/octet-stream

   000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
   --------------------------c4ae5238f12b6c82--
