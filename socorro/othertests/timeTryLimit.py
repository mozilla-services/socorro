import time
counter = 0
loops = 2000000
emptyCost = 0

arrayen = [ [1,2,3,4,5], [3,2,1]]
aIndex = 0

def anArray():
  global aIndex,arrayen
  aIndex = 1-aIndex;
  return arrayen[aIndex]

def display(diff,label,ignore=None):
  global constCost
  if emptyCost:
    diff -= emptyCost
  print label, 'time: %03.3f'%diff

def testEmpty(counting=False):
  ret = 0
  start = time.time()
  for i in range(loops):
    ret += anArray()[2]
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'empty',ret)

def testLength( counting=False):
  ret = 0
  start = time.time()
  for i in range(loops):
    a = anArray()
    if len(a) > 4:
      ret += a[4]
    else:
      ret += -1
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'length',ret)

def testTry( counting=False):
  ret = 0
  start = time.time()
  for i in range(loops):
    try:
      ret += anArray()[4]
    except:
      ret += -1
  stop = time.time()
  if counting: return stop -start
  else: display(stop-start,'tryit',ret)

display(testEmpty(True),'empty startup')
display(testTry(True),'tryit startup')
display(testEmpty(True),'empty startup')
display(testLength( True),'length startup')
display(testEmpty(True),'empty startup')

for i in range(5):
  emptyCost += testEmpty(True)
  print "empty cost at round %s is %s"%(i,emptyCost)
emptyCost /= 5
print "emptyCost is %s"%emptyCost
print "using two"
dt = testTry(True)
dl = testLength(True)
de = testEmpty(True)

dt += testTry(True)
dl += testLength(True)
de += testEmpty(True)

display(dt/2,'tryit')
display(dl/2,'length')
display(de/2,'empty')

print "using four"
de += testEmpty(True)
dl += testLength(True)
dt += testTry(True)
de += testEmpty(True)
dl += testLength(True)
dt += testTry(True)

display(de/4,'empty')
display(dl/4,'length')
display(dt/4,'tryit')
