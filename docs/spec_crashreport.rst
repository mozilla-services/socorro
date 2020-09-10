.. _crash-report-spec-chapter:

==========================================
Specification: Crash report payload format
==========================================

This is a specification for the format for submitting crash reports.

.. contents::
   :local:


crash report specification
==========================

History:

* 2020-01-15: Initial writing
* 2020-01-17: Add specifying annotations as a single JSON-encoded value.


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


Annotations as key/values in multipart/form-data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. The ``Content-Disposition`` must be ``form-data``.

2. The ``Content-Disposition`` must specify a ``name``. This is the annotation
   name. The value must be in ASCII.

3. The value of this field is the annotation value. It is always a string.

Example::

   Content-Disposition: form-data; name="AddonsShouldHaveBlockedE10s"

   1


Annotations as single JSON-encoded value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. The ``Content-Disposition`` must be ``form-data``.

2. The ``Content-Disposition`` must specify a ``name``. The value should
   be ``extra``. The value must be in ASCII.

3. The ``Content-Type`` must be ``application/json``.

4. The value of this field must a JSON-encoded string of all of the crash
   report annotations.

   Annotation keys and values must be strings.

   If the annotation value is an object, it must be a JSON-encoded string.
   Because the annotation value is a JSON-encoded string and it's in a
   JSON-encoded string, quotes must be escaped in the final field value.

5. There must be only one of this field.

Example::

   Content-Disposition: form-data; name="extra"
   Content-Type: application/json

   {"ProductName":"Firefox","Version":"1.0","TelemetryEnvironment":"{\"build\":{\"applicationName\":\"Firefox\",\"version\":\"72.0.1\",\"vendor\":\"Mozilla\"}}"}


.. Note::

   You must do either a JSON-encoded value for all annotations or specify each
   annotation as a multipart/form-data item. You can't do both.


.. versionadded:: 2020-01-17

   This was added in `bug 1420363
   <https://bugzilla.mozilla.org/show_bug.cgi?id=1420363>`_. That work landed
   in December 2019 and is in Firefox 73.


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


.. Note::

   It's possible for a crash report to be accepted by the collector, but be
   malformed in some way. For example, if one of the annotation values was
   ``null``. The processor has rules that will fix these issues and add
   processor notes for what it fixed.


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
      https://github.com/mozilla-services/antenna/blob/main/antenna/throttler.py


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

``has_json_and_kv``
   The crash report encodes annotations in ``multipart/form-data`` as well as
   in the extra JSON-encoded string. It should have either one or the
   other--not both.


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


Example with HTTP headers and body using JSON-encoded value for annotations::

   POST /submit HTTP/1.1
   Host: xyz.example.com
   User-Agent: Breakpad/1.0 (Linux)
   Accept: */*
   Content-Length: 659
   Content-Type: multipart/form-data; boundary=------------------------c4ae5238f12b6c82

   --------------------------c4ae5238f12b6c82
   Content-Disposition: form-data; name="extra"
   Content-Type: application/json

   {"ProductName":"Firefox","Version":"1.0","BuildID":"20160728203720"}
   --------------------------c4ae5238f12b6c82
   Content-Disposition: form-data; name="upload_file_minidump"; filename="6da3499e-f6ae-22d6-1e1fdac8-16464a16.dmp"
   Content-Type: application/octet-stream

   000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
   --------------------------c4ae5238f12b6c82--


How to debug crash report submission
====================================

1. When the crash reporter submits the crash report to Socorro, what is
   the status code that it gets back? What is the HTTP response body?

2. If you search for the crash id that Socorro returns, are there processor
   notes indicating problems?


If neither of those sets of questions are fruitful, please ask in one of our
channels.

https://github.com/mozilla-services/socorro/blob/main/README.rst
