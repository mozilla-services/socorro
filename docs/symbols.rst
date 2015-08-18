.. index:: symbols

How to pack and upload symbols
==============================

How to pack the symbols archive files
-------------------------------------

The minidump processor uses the binary filename (of the executable or shared
library) along with a debug ID (which is a GUID with one additional character)
to locate symbol files for each module in a minidump. Breakpad symbol files
as produced by the *dump_syms* tool contain all the information needed to
create the proper file paths in the first line of the file.

As a concrete example, if you run *dump_syms* on a single binary named
*test*::

    $ dump_syms ./test > test.sym
    $ head -n1 test.sym
    MODULE Linux x86_64 88886647D0C07CCA8B370069D9DF6F850 test
    $ mkdir -p symbols/test/88886647D0C07CCA8B370069D9DF6F850
    $ mv test.sym symbols/test/88886647D0C07CCA8B370069D9DF6F850
    $ find symbols -type f
    symbols/test/88886647D0C07CCA8B370069D9DF6F850/test.sym
    $ (cd symbols; zip -r9 ../symbols.zip *)
      adding: test/ (stored 0%)
      adding: test/88886647D0C07CCA8B370069D9DF6F850/ (stored 0%)
      adding: test/88886647D0C07CCA8B370069D9DF6F850/test.sym (deflated 71%)
    $ unzip -l symbols.zip
    Archive:  symbols.zip
      Length      Date    Time    Name
    ---------  ---------- -----   ----
            0  2015-08-18 07:10   test/
            0  2015-08-18 07:10   test/88886647D0C07CCA8B370069D9DF6F850/
         1056  2015-08-18 07:09   test/88886647D0C07CCA8B370069D9DF6F850/test.sym
    ---------                     -------
         1056                     3 files

The filename here is *test*, and the debug ID is the GUID shown. The contents of the *symbols* directory can be zipped up as shown and will work properly to symbolicate crash reports.

There are `a simple set of scripts <https://gist.github.com/luser/2ad32d290f224782fcfc>`
available for generating and uploading symbol zip files in the proper format.
You may also be interested in `symbolstore.py <https://dxr.mozilla.org/mozilla-central/source/toolkit/crashreporter/tools/symbolstore.py>`,
which is what official Firefox builds use to package their symbols.


How to upload
-------------

To be able to upload you need to have an account with which you
have the ``Upload Symbols Files`` permission.

Once you have that, visit https://crash-stats.mozilla.com/symbols/
and there will be two links presented there.

One to do a regular web file upload in the browser.

And one that takes you to the documentation about how to do uploads
using the API. That link will have links to where you can set up
API tokens.
