import time
import re
cRE = re.compile(r',(?! )')
cREp = re.compile(r'(?<=,)(?! )')
counter = 0
toRe = 'a,b, c, d,e,f, g, h,i,j,k, l, m, n,o,p,q'
loops = 200000
emptyCost = 0

def display(diff,label,ignore=None):
  global constCost
  if emptyCost:
    diff -= emptyCost
  print label, 'time: %03.3f'%diff

def empty(counting=False):
  start = time.time()
  for i in range(loops):
    ret = toRe
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'empty',ret)

def simple(counting=False):
  start = time.time()
  for i in range(loops):
    ret = cRE.sub(', ',toRe)
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'empty',ret)

def simpleRE(counting=False):
  start = time.time()
  for i in range(loops):
    ret = re.sub(cRE,', ',toRe)
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'empty',ret)

def fancy(counting=False):
  start = time.time()
  for i in range(loops):
    ret = cREp.sub(' ',toRe)
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'empty',ret)

def fancyRE(counting=False):
  start = time.time()
  for i in range(loops):
    ret = re.sub(cREp, ' ',toRe)
  stop = time.time()
  if counting: return stop-start
  else: display(stop-start, 'empty',ret)

display(empty(True),'empty startup')
display(simple(True),'simple startup')
display(simpleRE(True),'simpleRE startup')
display(empty(True),'empty startup')
display(fancy(True),'simple startup')
display(fancyRE(True),'simpleRE startup')
display(empty(True),'empty startup')

for i in range(5):
  emptyCost += empty(True)
emptyCost /= 5

print "using two"
ds =  simple(True)
df =  fancy(True)
dsr = simpleRE(True)
dfr = fancyRE(True)
de  = empty(True)
ds += simple(True)
df += fancy(True)
dsr+= simpleRE(True)
dfr+= fancyRE(True)
de += empty(True)

display(ds/2, 'simple')
display(dsr/2, 'simpleRE')
display(df/2, 'fancy')
display(dfr/2, 'fancyRE')
display(de/2, 'empty')

de += empty(True)
dfr+= fancyRE(True)
dsr+= simpleRE(True)
df += fancy(True)
ds += simple(True)
de += empty(True)
dfr+= fancyRE(True)
dsr+= simpleRE(True)
df += fancy(True)
ds += simple(True)

display(ds/4, 'simple')
display(dsr/4, 'simpleRE')
display(df/4, 'fancy')
display(dfr/4, 'fancyRE')
display(de/4, 'empty')
