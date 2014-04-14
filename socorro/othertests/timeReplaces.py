# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import time

numloops = 1000000
emptyCost = 0

ss = r'-L $dumpfileLocation -P$dumpfilePlan -d $dumpfilePathname -s $processorSymbolsPathnameList'
fixDumpfile = re.compile(r'\$dumpfilePathname')

def display(diff, label):
  global constCost
  diff -= emptyCost
  print label, 'time: %03.3f'%diff

def loop(counting = False):
  ret = 0
  start = time.time()
  for i in range(numloops):
    s = ss
    ret += len(s)
  stop = time.time()
  if counting:
    return stop-start
  else:
    display(stop-start,'empty:')
    return ret

def useRE(counting = False):
  ret = 0
  start = time.time()
  for i in range(numloops):
    s = fixDumpfile.sub('DUMPFILEPATHNAME',ss)
    ret += len(s)
  stop = time.time()
  if counting:
    return stop-start
  else:
    display(stop-start,'regex')
    return ret

def useReplace(counting = False):
  ret = 0
  start = time.time()
  for i in range(numloops):
    s = ss.replace('$dumpfilePathname','DUMPFILEPATHNAME')
    ret += len(s)
  stop = time.time()
  if counting:
    return stop-start
  else:
    display(stop-start,'repl:')
    return ret

loop()
useRE(True)
loop()
useReplace(True)
loop()
for i in range(5):
  emptyCost += loop(True)
emptyCost /= 5

loop()
useRE()
useRE()
useReplace()
useReplace()
loop()
useReplace()
useReplace()
loop()
useRE()
useRE()

