import os
import signal
import sys
import time


def getModuleFromFile(filename, depth=4, decorate=True):
  """
  Extract the bottom (depth) items in filename's path and return the items, dot-separated
  If fewer than depth: extract them all
  If decorate is boolean True, embed the module data in "\n==== %(module)s ====\n=====%(underline)s====="
  If decorate is a string, embed the module data as decorate%(data)
  Used to display which test is being run (helpful when multiple directories are nosetested from one command)
  """
  assert depth > 0, "You cannot ask for a depth less than one"
  template = "\n==== %(module)s ====\n=====%(underline)s====="
  if not decorate:
    template = "%(module)s"
  elif decorate and True != decorate:
    template = decorate
  if not filename:
    disp = "Unknown Module"
  else:
    disp = '.'.join(os.path.splitext(filename.lstrip(os.path.sep))[0].rsplit(os.path.sep,depth)[-depth:])
  bar = '='*len(disp)
  return template%({'module':disp,'underline':bar})

def nosePrintModule(filename,depth=4, decorate=True):
  print >> sys.stderr, getModuleFromFile(filename,depth,decorate)
  
def stopImmediately():
  return True;

def runInOtherProcess(executable, *args, **kwargs):
  maxWait = 1.0
  loopSleep = .1
  addWait = loopSleep
  maxWait = kwargs.get('maxWait',maxWait)
  stopCondition = kwargs.get('stopCondition',stopImmediately)
  logger = kwargs.get('logger',None) # Yes: Fail badly and obviously
  sygnal = kwargs.get('signal',signal.SIGHUP)
  if 0 == maxWait: # set maxWait = 0 to wait only on stopCondition
   addWait = 0.0 
  pid = os.fork()
  if(pid): # I am the parent. Wait a bit then kill -HUP the child
    # logger.debug("PARENT: P and C PIDs: (%s/%s)"%(os.getpid(),pid))
    waitedSoFar = 0.0
    while True:
      # logger.debug("PARENT: TOP WHILE (sleep time=%s)"%loopSleep)
      time.sleep(loopSleep)
      waitedSoFar += addWait
      # logger.debug("PARENT: WAITED WHILE")
      if stopCondition() or waitedSoFar >= maxWait:
#         if waitedSoFar >= maxWait:
#           logger.debug ("PARENT - STOP ON WAITED SO FAR %s"%waitedSoFar)
#         else:
#           logger.debug("PARENT - STOP ON CONDITION")
        break
    os.kill(pid,sygnal)
    # logger.debug("PARENT: SENT KILL")
    while True: # Child should be dead. os.wait() assures us it is done
      # logger.debug("PARENT: TOP OS.WAIT LOOP")
      wpid,info = os.wait()
      # logger.debug("WAITED: %s, %s"%(wpid,info))
      if wpid == pid: break
    # logger.debug("PARENT: ALL DONE")
  else: # I am the child process: Run the executable that will be killed
    try:
      executable(*args)
    except BaseException,x:
      os._exit(0)

