#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
A sample app that is able to exit and spit out specific messages on stdout
and stderr exactly as asked for.
This is used for testing the socorro.cron.base.SubprocessMixin class

To test this app run it like this::

    $ ./sampleapp.py 1 foo bar 1> out.log 2> err.log
    $ echo $?
    1
    $ cat out.log
    foo
    $ cat err.log
    bar

"""


if __name__ == '__main__':
    import sys
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("--exit", dest="exit_code", type="int", default=0)
    parser.add_option("-o", dest="out", default="")
    parser.add_option("-e", dest="err", default="")

    options, args = parser.parse_args()
    if options.out:
        print >>sys.stdout, options.out
    if options.err:
        print >>sys.stderr, options.err
    sys.exit(options.exit_code)
