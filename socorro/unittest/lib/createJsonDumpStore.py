import datetime as DT
import errno
import os
import time

import socorro.lib.JsonDumpStorage as JDS

def getSlot(minsperslot,minute):
  return minsperslot * int(minute/minsperslot)

def createTestSet(testData,jsonKwargs,rootDir):
  try:
    os.makedirs(rootDir)
  except OSError,x:
    if errno.EEXIST != x.errno: raise

  storage = JDS.JsonDumpStorage(rootDir, **jsonKwargs)
  thedt = DT.datetime.now()
  for uuid,data in testData.items():
    if data[0].startswith('+'):
      if thedt.second >= 58:
        print "\nSleeping for %d seconds" %(61-thedt.second)
        time.sleep(61-thedt.second)
        thedt = DT.datetime.now()
      slot = {
        '+0': getSlot(storage.minutesPerSlot,thedt.minute),
        '+5': getSlot(storage.minutesPerSlot,thedt.minute+5),
        '+10':getSlot(storage.minutesPerSlot,thedt.minute+10),
      }
      d3h = '%d/%02d/%02d/%02d/%s' %(thedt.year,thedt.month,thedt.day,thedt.hour,slot[data[0]])
      data[3] = "%s/%s" % (d3h,data[3])
    else:
      thedt = DT.datetime(*[int(x) for x in data[0].split('-')])
    fj,fd = storage.newEntry(uuid,webheadHostName=data[1],timestamp = thedt)
    try:
      fj.write('json test of %s\n' % uuid)
    finally:
      if fj: fj.close()
    try:
      fd.write('dump test of %s\n' % uuid)
    finally:
      if fd: fd.close()
