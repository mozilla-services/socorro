#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import numpy as np
import matplotlib.pyplot as plt
import pylab
import sys
import getopt
import string

products = [ "Firefox", "Firefox-4.0", "Fennec", "Thunderbird", "SeaMonkey" ]

def printable(input):
    return ''.join(filter(lambda x:x in string.printable, input))

def read_data(srcfile):
    data_dict = {}

    fin = open(srcfile, "r")
    for line in fin:
        splits = line.split('\t')
        if len(splits) == 5:
            date_str = splits[0]
            product_version = printable(splits[1] + " " + splits[2])
            label = splits[3]
            count = int(splits[4])

            if printable(splits[1].strip()) in products:
                label_dict = data_dict.setdefault(label, {})

                for k in [ product_version, "total" ]:
                    product_dict = label_dict.setdefault(k, {})
                    prev_count = product_dict.get(date_str, 0)
                    product_dict[date_str] = prev_count + count

    fin.close()

    return data_dict

def plot_product_version(product_version, data_dict):
    print "Product version: \"%s\"" % (product_version)
    date_counts = sorted(data_dict['submission'][product_version].items())
    dates, counts = [[z[i] for z in date_counts] for i in (0, 1)]
    plt.clf()
    plt.plot(counts, 'b-o', label='submissions')
    plt.xticks(np.arange(len(dates)), dates, rotation=75)
    plt.xlabel("Date")
    plt.ylabel("Count")
    plt.title("Socorro Crash Stats for %s" % (product_version))

    if data_dict['processed'].has_key(product_version):
        date_counts = sorted(data_dict['processed'][product_version].items())
        dates, counts = [[z[i] for z in date_counts] for i in (0, 1)]
        plt.plot(counts, 'g-s', label='processed', linewidth=2)

    if data_dict['oopp'].has_key(product_version):
        date_counts = sorted(data_dict['oopp'][product_version].items())
        dates, counts = [[z[i] for z in date_counts] for i in (0, 1)]
        plt.plot(counts, 'r-^', label='oopp')

    if data_dict['hang'].has_key(product_version):
        date_counts = sorted(data_dict['hang'][product_version].items())
        dates, counts = [[z[i] for z in date_counts] for i in (0, 1)]
        plt.plot(counts, 'm-x', label='hang')

    plt.legend(loc='best')
    plt.savefig("%s.png" % (product_version))

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

    data_dict = read_data(src_file)
    for product_version in data_dict['submission'].keys():
        plot_product_version(product_version, data_dict)


