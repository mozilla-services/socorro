# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import time
import re

sre = re.compile(r'[\\/]')

counter = 0
functions = ['C:\\Applications\Mozilla\\Mozilla Firefox\\contents\\xul\\layout_xul_tree.xpt',
             '/Applications/Mozilla.app/Mozilla Firefox/contents/xul/layout_xul_tree.xpt',
             'firefox',
             ]
loops = 1000000
emptyCost = 0
sp1 = 0
sp2 = 0
spre = 0

def display(diff,label,ignore=None):
  global constCost
  if emptyCost:
    diff -= emptyCost
  print label, 'time: %03.3f'%diff

def empty(counting=False):
  start = time.time()
  for i in range(loops):
    for j in functions:
      ret = j
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'empty',ret)

def splitter1(counting=False):
  start = time.time()
  for i in range(loops):
    for j in functions:
      if '\\' in j:
        ret = j.rstrip('\\').rsplit('\\',1)[-1]
      else:
        ret = j.rstrip('/').rsplit('/',1)[-1]
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'empty',ret)

def splitter2(counting=False):
  start = time.time()
  for i in range(loops):
    for j in functions:
      j = j.rstrip('/\\')
      if '\\' in j:
        ret = j.rsplit('\\',1)[-1]
      else:
        ret = j.rsplit('/',1)[-1]
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'empty',ret)

def splitRE(counting = False):
  start = time.time()
  for i in range(loops):
    for j in functions:
      j = j.rstrip('/\\')
      ret = sre.split(j)[-1]
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'empty',ret)


display(empty(True),'empty startup')
display(splitter1(True),'split1 tartup')
display(splitter2(True),'split2 startup')
display(splitRE(True),'splitRE startup')
display(empty(True),'empty startup')

for i in range(5):
  emptyCost += empty(True)
emptyCost /= 5

print "using two"
d1 =  splitter1(True)
d2 =  splitter2(True)
dr =  splitRE(True)
de =  empty(True)
d1 += splitter1(True)
d2 += splitter2(True)
dr += splitRE(True)
de += empty(True)

display(d1/2, 'splitter1')
display(d2/2, 'splitter2')
display(dr/2, 'splitRE')
display(de/2, 'empty')

print "using four"
de += empty(True)
dr += splitRE(True)
d2 += splitter2(True)
d1 += splitter1(True)
de += empty(True)
dr += splitRE(True)
d2 += splitter2(True)
d1 += splitter1(True)

display(d1/4, 'splitter1')
display(d2/4, 'splitter2')
display(dr/4, 'splitRE')
display(de/4, 'empty')

