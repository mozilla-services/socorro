# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import time
import sys

counter = 0
toslice = 'this is a string to slice'
loops = 3000000
emptyCost = 0

def display(start,stop,label):
  global constCost
  d = stop - start
  if emptyCost:
    d -= emptyCost
  print label, 'time: %03.3f'%d

def nilSlice(counting = False):
  start = time.time()
  for i in range(loops):
    counter = len(toslice)
  stop = time.time()
  if counting: return stop-start
  else: display(start,stop,'no slice')

def noSlice(counting=False):
  start = time.time()
  for i in range(loops):
    counter = len(toslice[:])
  stop = time.time()
  if counting: return stop-start
  else: display(start,stop,'[:] slice')

def smallSlice(counting=False):
  start = time.time()
  for i in range(loops):
    counter = len(toslice[:5])
  stop = time.time()
  if counting: return stop-start
  else: display(start,stop,'[:5] slice')

def equalSlice(counting=False):
  start = time.time()
  for i in range(loops):
    counter = len(toslice[:25])
  stop = time.time()
  if counting: return stop-start
  else:display(start,stop,'[:len] slice')

def bigSlice(counting=False):
  start = time.time()
  for i in range(loops):
    counter = len(toslice[:1000])
  stop = time.time()
  if counting: return stop-start
  else: display(start,stop,'[:len+] slice')

def hugeSlice(counting=False):
  start = time.time()
  for i in range(loops):
    counter = len(toslice[:10000])
  stop = time.time()
  if counting: return stop-start
  else: display(start,stop,'[:max] slice')


nilSlice(True)
equalSlice(True)
nilSlice(True)
hugeSlice(True)
nilSlice(True)
bigSlice(True)
for i in range(5):
  emptyCost += nilSlice(True)
emptyCost /= 5
print "Empty Cost is %03.3f"%emptyCost

d1 = hugeSlice(True)
d1 += hugeSlice(True)
display(0,d1/2,'slice [:10K]')
d2 = bigSlice(True)
d2 += bigSlice(True)
display(0,d2/2,'slice [:1K]')
d3 = equalSlice(True)
d3 += equalSlice(True)
display(0,d3/2,'slice [:len]')
d4 = smallSlice(True)
d4 += smallSlice(True)
display(0,d4/2,'slice [:5]')
d5 = noSlice(True)
d5 += noSlice(True)
display(0,d5/2,'slice [:]')
d6 = nilSlice(True)
d6 += nilSlice(True)
display(0,d6/2,'no slice')

print "\nREVERSE\n"

d6 += nilSlice(True)
d6 += nilSlice(True)
display(0,d6/4,'no slice')
d5 += noSlice(True)
d5 += noSlice(True)
display(0,d5/4,'slice [:]')
d4 += smallSlice(True)
d4 += smallSlice(True)
display(0,d4/4,'slice [:5]')
d3 += equalSlice(True)
d3 += equalSlice(True)
display(0,d3/4,'slice [:len]')
d2 += bigSlice(True)
d2 += bigSlice(True)
display(0,d2/4,'slice [:1K]')
d1 += hugeSlice(True)
d1 += hugeSlice(True)
display(0,d1/4,'slice [:10K]')
