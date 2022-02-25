.. _crash-report-spec-chapter:

=======================================
Specification: Submitting crash reports
=======================================

.. contents::
   :local:


Summary
=======

The Breakpad library includes an `HTTP upload tool
<https://chromium.googlesource.com/breakpad/breakpad/+/master/src/tools/linux/symupload/minidump_upload.cc>`_.
However, Mozilla doesn't use that tool for its products. Instead, we have our
own set of crash reporting clients.

This specification covers the HTTP POST request and response for submitting
crash reports to the Socorro collector.



History
=======

History:

* 2020-01-15: Initial writing
* 2020-01-17: Add specifying annotations as a single JSON-encoded value.
* 2021-05-26: Add notes about where we stray from the Breakpad crash reporting
  client.
* 2021-12-20: Generalize to cover HTTP POST request and response for the
  Socorro collector.


Crash reporter client submission request
========================================

Request method
--------------

Crash reports are submitted by HTTP POST to the Socorro collector crash
submission URL.


Request headers
---------------

The HTTP POST request must include the following headers:

``Content-Type``

   The content type header of the crash report must be either
   ``multipart/form-data`` or ``multipart/mixed`` and it must specify the
   multipart boundary.

``Content-Length``

   The content length of the crash report must be set. The value is the length
   of the body.

``Content-Encoding`` (optional)

   If the HTTP body is gzipped, then the ``Content-Encoding`` must be set to
   ``gzip``.

   Generally, it's good to compress bodies since it reduces the size of the
   body, reduces the time it takes to upload, and also increases the size of
   the crash reports you can send.


Request body
------------

The crash report is in the HTTP POST body and consists of crash annotations and
dumps.

If the ``Content-Encoding`` header is set to ``gzip``, the body must be
gzipped.


Crash annotations
~~~~~~~~~~~~~~~~~

The body consists of a series of multipart fields. Each field is either an
annotation or a binary like a minidump.

.. seealso::

   RFC for multipart/form-data and multipart/mixed:
      https://tools.ietf.org/html/rfc7578

There are two ways to provide crash annotations:

1. annotations as key/value pairs, OR
2. annotations as a single JSON-encoded value

You can provide crash annotations as EITHER key/value pairs, OR a JSON-encoded
value for all annotations--you can't do both.


Annotations as key/value pairs in form-data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. The ``Content-Disposition`` must be ``form-data``.

2. The ``Content-Disposition`` must specify a ``name``. This is the annotation
   name. The value must consist of ASCII characters.

3. The value of this field is the annotation value. It is always a string.

Example::

   Content-Disposition: form-data; name="DOMFissionEnabled"

   1


Annotations as single JSON-encoded value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. The ``Content-Disposition`` must be ``form-data``.

2. The ``Content-Disposition`` must specify a ``name``. The value should
   be ``extra``.

3. The ``Content-Type`` must be ``application/json``.

4. The value of this field must a JSON-encoded object of all of the crash
   report annotations.

   All annotation keys and values must be strings.

   If the annotation value is an object, it must be JSON-encoded. Because the
   annotation value is JSON-encoded object and it is itself in a JSON-encoded
   object, quotes must be escaped in the final field value.

5. There must be only one "extra" field in the payload.

Example::

   Content-Disposition: form-data; name="extra"
   Content-Type: application/json

   {"ProductName":"Firefox","Version":"1.0","TelemetryEnvironment":"{\"build\":{\"applicationName\":\"Firefox\",\"version\":\"72.0.1\",\"vendor\":\"Mozilla\"}}"}


.. versionadded:: 2020-01-17

   This was added in `bug 1420363
   <https://bugzilla.mozilla.org/show_bug.cgi?id=1420363>`_. That work landed
   in December 2019 and is in Firefox 73.


Dumps and other binary data
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. The ``Content-Disposition`` must be ``form-data``.

2. The ``Content-Disposition`` must specify a ``name``. The name must consist
   of ASCII characters.

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


.. Note::

   The Socorro processor treats the name ``upload_file_minidump`` as the
   minidump of the crashing process. It extracts information from it and that's
   what shows up on Crash Stats.

   If you're writing your own crash reporter client, you should make sure to
   set the name for dump for the crash report as ``upload_file_minidump``.


Collector response
==================

The collector throttles crash reports and returns a response to the crash
reporter client in the HTTP response.

HTTP 200
    Crash report submission was successful.

    Accepted:
        If the crash report is accepted by the collector, then the collector
        must return an HTTP status code of 200 with a body specifying the crash
        id::

           "CrashID" "=" CRASHID

        For example::

           CrashID=bp-d101d046-638f-42e0-902d-bd245c200115


        .. Note::

           It's possible for a crash report to be accepted by the collector,
           but be malformed in some way. For example, if one of the annotation
           values was ``null``. The processor has rules that will fix these
           issues and add processor notes for what it fixed.


    Rejected:
        If the crash report is rejected by the collector, then the collector
        must return an HTTP status code of 200 with a body specifying the
        rejection rule::

           "Discarded" "=" RULE

        For example::

           Discarded=rule_has_hangid_and_browser

        Rejection rules are specified in the collector's throttler. They change
        periodically.

        Some rejection rules are hard-rejections and the collector will never
        accept the crash report.

        Some rejection rules are soft-rejections from sampling and the
        collector may accept that crash report again in the future.

        The crash reporter client may submit the crash report again.

        .. seealso::

           Code for throttler:
              https://github.com/mozilla-services/antenna/blob/main/antenna/throttler.py


HTTP 400
    If the crash report is malformed, then the collector must return an HTTP
    status code of 400 with a body specifying the malformed reason::

       "Discarded" "=" REASON

    For example::

       Discarded=no_annotations


    Non-exhaustive list of reasons the crash report could be malformed:

    ``no_content_type``
       The crash report HTTP POST has no content type in the HTTP headers.

    ``wrong_content_type``
      The crash report HTTP POST content type header exists, bug it's not set
      to ``multipart/form-data`` or ``multipart/mixed.

    ``no_boundary``
       The content type doesn't include a boundary value, so it can't be parsed
       as ``multipart``.

    ``bad_gzip``
       The ``Content-Encoding`` header is set to ``gzip``, but the body isn't
       in gzip format or there's a parsing error.

    ``no_annotations``
       The crash report has been parsed, but there were no annotations in it.

    ``has_json_and_kv``
       The crash report encodes annotations as ``form-data`` fields as well as
       in an extra JSON-encoded object. It should have either one or the
       other--not both.


    The crash reporter client shouldn't try to send a malformed crash report
    again.

HTTP 413
    The HTTP POST body is too large and exceeds the maximum body size.

    The crash reporter client shouldn't try to send this crash report again.


HTTP 500
    This is an internal server error.

    It's possible this is a bug in the collector. If so, an error report gets
    sent and maintainers will see it.

    It's possible this problem is ephemeral and will go away after some time.

    The crash reporter client may sleep for a bit and retry sending the
    crash report.

HTTP 502
    Bad gateway.

    It's possible this problem is ephemeral and will go away after some time.
    It's possible that this is a bug in the crash reporting client.

    The crash reporter client may sleep for a bit and retry sending the
    crash report.

HTTP 503
    Service unavailable.

    It's possible this problem is ephemeral and will go away after some time.

    The crash reporter client may sleep for a bit and retry sending the
    crash report.


Example of crash report HTTP POST
=================================

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
   Content-Disposition: form-data; name="DOMFissionEnabled"

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


Differences from Breakpad upload tool
=====================================

The Breakpad library comes with an upload tool. That tool lets you upload crash
annotations and dumps as an HTTP POST to a collector.

It does not support the following things in this specification:

1. returning crash id on successful submission
2. returning rejection code on rejected crash report
3. crash annotations as a single JSON-encoded value


How to debug problems with submitting crash reports
===================================================

We hang out in `#crashreporting:mozilla.org
<https://riot.im/app/#/room/#crashreporting:mozilla.org>`_.

Here are some notes for issues you might be having:

**I'm getting back an HTTP 404**

The URL you're using is wrong. Verify the url. If that doesn't work, reach out
to us.

**I'm getting back an HTTP 413**

The crash report request body is too large. If you aren't compressing it with
gzip, try that. If you are, then reach out to us but you're probably going to
need to remove something.

**I'm getting back a rejection**

Check the response body for the rejection code and look it up in the throttling
rules:

https://github.com/mozilla-services/antenna/blob/main/antenna/throttler.py

If that doesn't help, reach out to us.

**I'm getting back an HTTP 500**

Reach out to us because something is wrong with our server.

**The crash report submitted, but there's very little data on Crash Stats**

Verify that the name (not the filename) is set to "upload_file_minidump".  The
Socorro processor treats that specific minidump as the one for the crashed
process and does additional processing for it.

You can see a list of all the dumps that were sent in the Debug tab of the
report view on Crash Stats.

Verify that you're sending all the crash annotations you're intending to
send.

You can see a list of all the dump names and crash annotations in the
``crash_report_keys`` field of the processed crash.

If this is a new crash annotation or one that's not explicitly marked
as public, the crash annotation will be treated as protected data. If you
don't have access to protected data, you will not be able to see it on
Crash Stats.

See our protected data access policy:

https://crash-stats.allizom.org/documentation/protected_data_access/

**None of these are helping me**

Ask yourself these questions and see if they help you at all:

1. When the crash reporter client submits the crash report to Socorro, what is
   the status code that it gets back? What is the HTTP response body?

2. If you successfully submit a crash report, search for the crash id on Crash
   Stats. Are there processor notes indicating problems?

If nothing here helps please reach out to us on Matrix.
