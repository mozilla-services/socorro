import datetime
import os
import signal
import sys
import time
import socorro.lib.dynamicConfigurationManager as dcm

"""
Nosetests sometimes gets a little weird around multi-process testing. Isolate it here
"""

# def plog(*args, **kwargs):
#   """_P_seudo-_log_ that I didn't have to think about configuring"""
#   fn = 'dyconfigLog.txt'
#   try:
#     fh = open(fn,'a+')
#     fh.write(' '.join(str(x) for x in args)+"\n")
#     for k,v in kwargs.items():
#       fh.write(" %s [%s]\n"%(k,str(v)))
#   finally:
#     if fh:
#       fh.close()

# The meat of the test is actually right here: We use mark as the updateFunction
globalmarks = []
def mark(item):
  global globalmarks
  anId = item.myId
  aSyg = item.internal.signalNumber
  globalmarks.append((anId,aSyg))

# A semi-reasonable list of signums: SIGALRM, SIGINFO, SIGUSR1, SIGUSR2
sygnals = [14,29,30,31]

class TestDynamicConfigHandleSignal:
  def beChild(self,n):
    configs = []
    for sygnal in sygnals:
      conf = dcm.DynamicConfig(signalNumber=sygnal)
      lockf = None
      try:
        lockf = open("lock_%s.lck"%n,'a')
        lockf.write("config (%s) is constructed\n"%sygnal)
        conf.internal.updateFunction=mark
      finally:
        if lockf:
          lockf.close()
      conf['myId'] = "CHILE %s_%s"%(n,sygnal)
      configs.append(conf)
    # signals wake the sleeping, so we have to loop this way
    while True:
      time.sleep(1)
      if len(globalmarks) == len(sygnals):
        break
    ret = 0
    for aSyg in sygnals:
      if not ("CHILE %d_%d"%(n,aSyg),aSyg) in globalmarks:
        ret = 2
    for id,aSyg in globalmarks:
      expId = "CHILE %d_%d"%(n,aSyg)
      if expId != id or aSyg not in sygnals:
        ret |= 4
    os._exit(ret)
    
  def awaitAllChildren(self,childIds):
    """Don't start sending signals until the kids are ready to catch 'em"""
    for num,pid in childIds:
      lines = []
      lfname = "lock_%s.lck"%num
      now = datetime.datetime.now()
      # don't wait forever on error. Note: giveup is way too big, but it should not matter
      giveup = now + datetime.timedelta(seconds=len(sygnals)*len(childIds))
      while len(lines) < len(sygnals) and now < giveup:
        lockf = None
        try:
          try:
            lockf = open(lfname,'r')
            lines = lockf.readlines()
          except IOError,x:
            if not 2 == x.errno: raise
        finally:
          if lockf: lockf.close()
        time.sleep(.05)
        now = datetime.datetime.now()
      if len(lines) >= len(sygnals):
        os.unlink(lfname)
      assert now < giveup, "Did not create sufficient"
        
  def beParent(self,**kwargs):
    for sygnal in sygnals:
      for num,id in kwargs['childIds']:
        time.sleep(.05) # probably doesn't matter, but it probably doesn't hurt either
        os.kill(id,sygnal)
      time.sleep(.05)
    results = []
    for num,pid in kwargs['childIds']:
      # waitpid gives us 256
      wpid,value = os.waitpid(pid,0)
      assert 0 == (value >> 8), 'but got %d'%(value >> 8)

  def testHandleAlarm(self):
    childIds = []
    numkids = 1 # for a total of 12 signal/catch events
    for i in range(numkids):
      pid = os.fork()
      if pid:
        childIds.append((i,pid))
      else:
        self.beChild(i)
        break
    # If we are the parent, we know all the kids.
    if numkids == len(childIds):
      # Wait for the kids to tell us they are ready
      self.awaitAllChildren(childIds)
      # Do the actual test
      self.beParent(childIds = childIds)
      
