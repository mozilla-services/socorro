#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import numpy as np
from scipy import stats

def read_data(srcfile):
    data = []

    fin = open(srcfile, "r")
    for line in fin:
        splits = line.split('\t')
        data.append(int(splits[1]))

    fin.close()

    return data

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

if __name__ == "__main__":
    src_file = None
    try:
        try:
            opts, args = getopt.getopt(sys.argv[1:], "hs:", ["help"])

            for o, a in opts:
                if o in ("-h", "--help"):
                    print __doc__
                    raise Usage("-s <input file>")
                elif o == "-s":
                    src_file = a
        except getopt.error, msg:
            raise Usage(msg)
            # more code, unchanged
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"

    data = read_data(src_file)
    mean = stats.mean(data)
    median = stats.median(data)

