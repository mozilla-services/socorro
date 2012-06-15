#!/usr/bin/python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is find-interesting-modules.py.
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   L. Xavier Stevens, Mozilla Corporation (original author)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

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
