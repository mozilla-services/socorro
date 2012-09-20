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

size_kb = float(1024)
tab_pattern = re.compile("\t")
print "Reading file: " + sys.argv[1]
fin = open(sys.argv[1], "r")
sizes = []
threads = []
for line in fin:
    splits = tab_pattern.split(line.strip())
    if len(splits) == 6:
        ooid = splits[0].strip()
        day = splits[1].strip()
        product_version = splits[2].strip() + " " + splits[3].strip()
        raw_size = float(splits[4].strip()) / size_kb
        num_threads = int(splits[5].strip())
        sizes.append(raw_size)
        threads.append(num_threads)
fin.close()

print "Threads size: %d Sizes: %d" % (len(threads), len(sizes))
for i in range(len(threads)):
    if threads[i] < 0 or sizes[i] < 0:
        print "Threads: %d Sizes: %d" % (threads[i], sizes[i])

plt.clf()
f = pylab.gcf()
default_size = f.get_size_inches()
f.set_size_inches( (default_size[0]*2, default_size[1]*2) )
plt.axis([0, np.amax(threads), 0, np.amax(sizes) ])
plt.xlabel("# of Threads")
plt.ylabel("Size (in KBs)")
plt.title("Threads vs. Raw Dump Size")
plt.scatter(threads, sizes, alpha=0.25)

plt.savefig("threads-vs-dumpsize.png")
