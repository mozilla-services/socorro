import time
import re

loops = 1000000
emptyCost = 0

items = [None,'a',0,'b','','d']


def display(diff,label,ignore=None):
  global constCost
  if emptyCost:
    diff -= emptyCost
  print label, 'time: %03.3f'%diff

def empty(counting=False):
  ret = 0
  start = time.time()
  for i in range(loops):
    for j in items:
      ret += 1
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'empty',ret)

def ifelse(counting=False):
  ret = 0
  start = time.time()
  for i in range(loops):
    for j in items:
      if j:
        ret += 2
      else:
        ret -= 1
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'empty',ret)

def arrayit(counting=False):
  ret = 0
  start = time.time()
  for i in range(loops):
    for j in items:
      ret += [-1,2][bool(j)]
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'empty',ret)

display(empty(True),'empty startup')
display(ifelse(True),'ifelse startup')
display(arrayit(True),'arrayit startup')
display(empty(True),'empty startup')

for i in range(5):
  emptyCost += empty(True)
emptyCost /= 5

print "using two"
d1 =  ifelse(True)
d2 =  arrayit(True)
de =  empty(True)
d1 += ifelse(True)
d2 += arrayit(True)
de += empty(True)

display(d1/2, 'ifelse')
display(d2/2, 'arrayit')
display(de/2, 'empty')

print "using four"
de += empty(True)
d2 += arrayit(True)
d1 += ifelse(True)
de += empty(True)
d2 += arrayit(True)
d1 += ifelse(True)

display(d1/4, 'ifelse')
display(d2/4, 'arrayit')
display(de/4, 'empty')

