============================
Breakpad and crash reporters
============================

Links about breakpad
====================

Breakpad project home page:
    https://chromium.googlesource.com/breakpad/breakpad

Firefox Breakpad page:
    https://wiki.mozilla.org/Breakpad

    Note: A lot of this is out of date.

Socorro docs:
    http://socorro.readthedocs.io/en/latest/

    Notes on testing collector and processor:
    http://socorro.readthedocs.io/en/latest/configuring-socorro.html#test-collection-and-processing


Where do reports come from?
===========================

From Ted:

    We use different code to submit crash reports on all 4 major platforms we ship
    Firefox on: Windows, OS X, Linux, Android, and we also have a separate path for
    submitting crash reports from within Firefox (for crashes in content processes,
    plugin processes, and used when you click an unsubmitted report in
    about:crashes).

    For all the desktop platforms, the crashreporter client (the window that says
    "We're Sorry") is some C++ code that lives here:
    https://dxr.mozilla.org/mozilla-central/source/toolkit/crashreporter/client/

    For Windows the submission code in the client is here:
    https://dxr.mozilla.org/mozilla-central/rev/8d0aadfe7da782d415363880008b4ca027686137/toolkit/crashreporter/client/crashreporter_win.cpp#391

    which calls into Breakpad code here:
    https://dxr.mozilla.org/mozilla-central/rev/8d0aadfe7da782d415363880008b4ca027686137/toolkit/crashreporter/google-breakpad/src/common/windows/http_upload.cc#65

    which uses WinINet APIs to do most of the hard work. If you look near the
    bottom of that function you can see that it does require a HTTP 200 response
    code for success, but it doesn't look like it cares about the response
    content-type.

    For OS X the submission code is here:
    https://dxr.mozilla.org/mozilla-central/rev/8d0aadfe7da782d415363880008b4ca027686137/toolkit/crashreporter/client/crashreporter_osx.mm#555

    It uses Cocoa APIs to do the real work. It also checks for HTTP status 200 for success.

    For Linux the submission code is here:
    https://dxr.mozilla.org/mozilla-central/rev/8d0aadfe7da782d415363880008b4ca027686137/toolkit/crashreporter/client/crashreporter_gtk_common.cpp#190

    which calls into Breakpad code here:
    https://dxr.mozilla.org/mozilla-central/rev/8d0aadfe7da782d415363880008b4ca027686137/toolkit/crashreporter/google-breakpad/src/common/linux/http_upload.cc#57

    which calls into libcurl to do the work. It's a little hard for me to read,
    but it sets CURLOPT_FAILONERROR, which says it will only fail if the server
    returns a HTTP response code of 400 or higher, I believe.

    For Android the submission code is here:
    https://dxr.mozilla.org/mozilla-central/rev/8d0aadfe7da782d415363880008b4ca027686137/mobile/android/base/java/org/mozilla/gecko/CrashReporter.java#356

    which uses Java APIs. The Android client *does* gzip-compress the request
    body, and it also looks like it checks for HTTP 200
    (HttpURLConnection.HTTP_OK).

    For the in-browser case, the submission code is here:
    https://dxr.mozilla.org/mozilla-central/rev/8d0aadfe7da782d415363880008b4ca027686137/toolkit/crashreporter/CrashSubmit.jsm#253

    It uses XMLHttpRequest to submit, and it checks for HTTP status 200. I do
    note that it uses `responseText` on the XHR, so I'd have to read the XHR
    spec to see if that would break if the content-type of the response changed.
