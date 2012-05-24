#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import re
import numpy as np
import matplotlib.pyplot as plt
import pylab
import sys
import getopt
import string

products = [ "Firefox", "Firefox-4.0", "Fennec", "Thunderbird", "SeaMonkey" ]

def printable(input):
    return ''.join(filter(lambda x:x in string.printable, input))

def plot_product_version_total(product_version, dates, raw, processed):
    plt.clf()
    plt.plot(raw, 'b-o', label='raw')
    plt.xticks(np.arange(len(dates)), dates, rotation=75)
    plt.xlabel("Date")
    plt.ylabel("Size (in GBs)")
    plt.title("Crash Dump Total Size Trend for %s" % (product_version))

    plt.plot(processed, 'g-s', label='processed', linewidth=2)

    plt.legend()
    plt.savefig("%s Total.png" % (product_version))

def plot_product_version_median(product_version, dates, raw, processed):
    plt.clf()
    plt.plot(raw, 'b-o', label='raw')
    plt.xticks(np.arange(len(dates)), dates, rotation=75)
    plt.xlabel("Date")
    plt.ylabel("Size (in KBs)")
    plt.title("Crash Dump Median Size Trend for %s" % (product_version))

    plt.plot(processed, 'g-s', label='processed', linewidth=2)

    plt.legend()
    plt.savefig("%s Median.png" % (product_version))

data = {}
size_kb = float(1024)
size_gb = float(1073741824)
tab_pattern = re.compile("\t")
print "Reading file: " + sys.argv[1]
fin = open(sys.argv[1], "r")
median_min = 10000000
median_max = 0
total_min = 10000000
total_max = 0
date_set = set([])
valid_version = re.compile("^(1\.[0-9]|3\.[056][\.0-9]{0,3}|4\.0b[0-9])$")
for line in fin:
    splits = tab_pattern.split(line.strip())
    if len(splits) == 7:
        day = splits[0].strip()
        product_name = splits[1].strip()
        version = splits[2].strip()
        if printable(product_name) not in products:
            continue

        if not valid_version.match(version):
            continue

        product_version = splits[1] + " " + splits[2]
        data_type = splits[3].strip()
        day_count = int(splits[4].strip())
        median_size = float(splits[5].strip()) / size_kb
        total_size = long(splits[6].strip()) / size_gb

        date_set.add(day)

        product = data.setdefault(product_version, [])
        product.append({ 'product': product_name, 'version': version, 'date': day, 'type': data_type, 'median': median_size, 'total': total_size })
        data[product_version] = product

        if median_size < median_min:
            median_min = median_size
        elif median_size > median_max:
            median_max = median_size

        if total_size < total_min:
            total_min = total_size
        elif total_size > total_max:
            total_max = total_size

fin.close()

'''
dates = sorted(list(date_set))
for product_version,data_list in data.iteritems():
    if len(data_list) <= 2:
        continue

    print "Plotting Product Version Totals: " + product_version
    raw_totals = np.zeros(len(dates))
    processed_totals = np.zeros(len(dates))
    for d in data_list:
        for i in range(0,len(dates)):
            if dates[i] == d['date']:
                if d['type'] == 'raw':
                    raw_totals[i] = d['total']
                elif d['type'] == 'processed':
                    processed_totals[i] = d['total']

                break

    plot_product_version_total(product_version, dates, raw_totals, processed_totals)

for product_version,data_list in data.iteritems():
    if len(data_list) <= 2:
        continue

    print "Plotting Product Version Medians: " + product_version
    raw_medians = np.zeros(len(dates))
    processed_medians = np.zeros(len(dates))
    for d in data_list:
        for i in range(0,len(dates)):
            if dates[i] == d['date']:
                if d['type'] == 'raw':
                    raw_medians[i] = d['median']
                elif d['type'] == 'processed':
                    processed_medians[i] = d['median']

                break

    plot_product_version_median(product_version, dates, raw_medians, processed_medians)
'''
#print "Median min: %0.2f max: %0.2f" % (median_min, median_max)
#print "Total min: %0.2f max: %0.2f" % (total_min, total_max)

print json.dumps(data, sort_keys=True, indent=2)
