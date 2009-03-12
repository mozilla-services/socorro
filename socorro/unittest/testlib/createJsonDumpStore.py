import datetime as DT
import errno
import os
import time

import simplejson

import socorro.lib.JsonDumpStorage as JDS

jsonFileData = {
  '0bba61c5-dfc3-43e7-dead-8afd20071025': ('2007-10-25-05-04','webhead02','0b/ba/61/c5','2007/10/25/05/00/webhead02_0'),
  '0bba929f-8721-460c-dead-a43c20071025': ('2007-10-25-05-04','webhead02','0b/ba/92/9f','2007/10/25/05/00/webhead02_0'),
  '0b9ff107-8672-4aac-dead-b2bd20081225': ('2008-12-25-05-00','webhead01','0b/9f/f1/07','2008/12/25/05/00/webhead01_0'),
  '22adfb61-f75b-11dc-dead-001320081225': ('2008-12-25-05-01','webhead01','22/ad/fb/61','2008/12/25/05/00/webhead01_0'),
  'b965de73-ae90-a935-dead-03ae20081225': ('2008-12-25-05-04','webhead01','b9/65/de/73','2008/12/25/05/00/webhead01_0'),
  '0b781b88-ecbe-4cc4-dead-6bbb20081225': ('2008-12-25-05-05','webhead01','0b/78/1b/88','2008/12/25/05/05/webhead01_0'),
  '0b8344d6-9021-4db9-dead-a15320081225': ('2008-12-25-05-06','webhead01','0b/83/44/d6','2008/12/25/05/05/webhead01_0'),
  '0b94199b-b90b-4683-dead-411420081226': ('2008-12-26-05-21','webhead01','0b/94/19/9b','2008/12/26/05/20/webhead01_0'),
  '0b9eedc3-9a79-4ce2-dead-155920081226': ('2008-12-26-05-24','webhead01','0b/9e/ed/c3','2008/12/26/05/20/webhead01_0'),
  '0b9fd6da-27e4-46aa-dead-3deb20081226': ('2008-12-26-05-25','webhead02','0b/9f/d6/da','2008/12/26/05/25/webhead02_0'),
  '0ba32a30-2476-4724-dead-de17e3081125': ('2008-11-25-05-00','webhead02','0b/a3/2a','2008/11/25/05/00/webhead02_0'),
  '0bad640f-5825-4d42-dead-21b8e3081125': ('2008-11-25-05-04','webhead02','0b/ad/64','2008/11/25/05/00/webhead02_0'),
  '0bae7049-bbff-49f2-dead-7e9fe2081125': ('2008-11-25-05-05','webhead02','0b/ae','2008/11/25/05/05/webhead02_0'),
  '0baf1b4d-dad3-4d35-dead-b9dce2081125': ('2008-11-25-05-06','webhead02','0b/af','2008/11/25/05/05/webhead02_0'),
}

jsonMoreData =  {
  '28adfb61-f75b-11dc-b6be-001320081225': ('2008-12-25-05-01','webhead01','28/ad/fb/61','2008/12/25/05/00'),
  '29adfb61-f75b-11dc-b6be-001320081225': ('2008-12-25-05-00','webhead01','29/ad/fb/61','2008/12/25/05/00'),
}

jsonTooMany = {
  '23adfb61-f75b-11dc-b6be-001320081225': ('2008-12-25-05-01','webhead01','23/ad/fb/61','2008/12/25/05/00'),
  '24adfb61-f75b-11dc-b6be-001320081225': ('2008-12-25-05-01','webhead01','24/ad/fb/61','2008/12/25/05/00'),
  '25adfb61-f75b-11dc-b6be-001320081225': ('2008-12-25-05-02','webhead01','25/ad/fb/61','2008/12/25/05/00'),
  '26adfb61-f75b-11dc-b6be-001320081225': ('2008-12-25-05-02','webhead01','26/ad/fb/61','2008/12/25/05/00'),
  '27adfb61-f75b-11dc-b6be-001320081225': ('2008-12-25-05-03','webhead01','27/ad/fb/61','2008/12/25/05/00'),
  }


jsonBadUuid = '66666666-6666-6666-6666-666620081225'

def getSlot(minsperslot,minute):
  return minsperslot * int(minute/minsperslot)

def minimalJsonFileContents(dataMap = None):
  if not dataMap:
    dataMap = {'ProductName':'bogusName-%02d',
               'Version':'bogusVersion-%02d',
               'BuildID':'bogusBuildID-%02d',
               }
    cookie = 0
    while True:
      retMap = {}
      for k,v in dataMap.entries():
        retMap[k] = v%cookie
      yield simplejson.dumps(retMap)

def createTestSet(testData,jsonKwargs,rootDir):
  try:
    os.makedirs(rootDir)
  except OSError,x:
    if errno.EEXIST != x.errno: raise

  storage = JDS.JsonDumpStorage(rootDir, **jsonKwargs)
  jsonIsEmpty = jsonKwargs.get('jsonIsEmpty', False)
  jsonIsBogus = jsonKwargs.get('jsonIsBogus', True)
  jsonFileGenerator = jsonKwargs.get('jsonFileGenerator',None)
  if 'default' == jsonFileGenerator:
    jsonFileGenerator = minimalJsonFileContents
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
      if jsonIsEmpty:
        pass
      elif jsonIsBogus:
        fj.write('json test of %s\n' % uuid)
      else:
        if jsonFileGenerator:
          fileContents = jsonFileGenerator.next()
        else:
          fileContents = '{"what": "legal json, bad contents", "uuid": "%s\"}\n'% uuid
        fj.write(fileContents)
    finally:
      if fj: fj.close()
    try:
      fd.write('dump test of %s\n' % uuid)
    finally:
      if fd: fd.close()
