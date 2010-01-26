import copy
import datetime
import os
import psycopg2
import time

import socorro.lib.ConfigurationManager as cm
import socorro.lib.dynamicConfigurationManager as dcm

import socorro.unittest.testlib.util as tutil

import dbTestconfig as dbConfig
import dynamicTestconfig as dyConfig

def setup_module():
  tutil.nosePrintModule(__file__)

# used to test conversion function in defaultDbUpdater
def weird(item):
  return ('w',int(item),int(item)/1.5)

class TestDynamicConfigurationManager:
  def setUp(self):
    self.config = cm.newConfiguration(configurationModule = dbConfig, applicationName = 'testDynamicConfigurationManager')
    dbData = (self.config.databaseHost,self.config.databaseName,self.config.databaseUserName,self.config.databasePassword)
    dsn = "host=%s dbname=%s user=%s password=%s" % dbData
    self.connection = psycopg2.connect(dsn)
    cursor = self.connection.cursor()
    cursor.execute('drop table if exists dbConfig cascade')
    
  def tearDown(self):
    cursor = self.connection.cursor()
    cursor.execute('drop table if exists dbConfig cascade')
    self.connection.commit()
    self.connection.rollback()
    self.connection.close()

  def testDefaultExecUpdater(self):
    testDir = os.path.dirname(__file__)
    tu = dcm.createDefaultExecUpdater(os.path.join(testDir,'dynamicTestconfig.py'))
    assert 'testOption0' not in self.config
    assert 'testOption1' not in self.config
    assert 'logFilePathname' in self.config
    priorLogPath = self.config['logFilePathname']
    c2 = copy.copy(self.config)
    tu(c2)
    assert 0 == c2['testOption0']
    assert 'one' == c2['testOption1']
    assert priorLogPath != c2['logFilePathname']

  def testDefaultDbUpdater(self):
    cur = self.connection.cursor()
    cur.execute("CREATE TABLE dbConfig(configKey text primary key, configValue text, configConversion text)")
    dbData = [
      ['testOption0','0','int',0],
      ['testOption1','one',None,'one'],
      ['testOption_5','0.5','float',0.5],
      ['weirdOption','12','weird',('w',12,8.0)],
      ['aDateTime','2009-12-25 12:12:12','dateTimeConverter',datetime.datetime(2009,12,25,12,12,12)],
      ['anInterval','1:2:3:4','timeDeltaConverter',datetime.timedelta(days=1,hours=2,minutes=3,seconds=4)],
      ['booleanTrue','True','booleanConverter',True],
      ['boolean1','1','booleanConverter',True],
      ['boolean0','0','booleanConverter',False],
     ]
    insData = [x[:3] for x in dbData]
    cur.executemany("INSERT INTO dbconfig (configKey,configValue,configConversion) VALUES (%s,%s,%s)",insData)
    self.connection.commit()
    dcm.weird = weird
    dbu = dcm.createDefaultDbUpdater(cur,'dbconfig')
    s = {}
    dbu(s)
    for k,v,conv,ignor in dbData:
      assert v == s[k], 'Expected "%s" but got "%s"'%(v,s[k])
    dbu = dcm.createDefaultDbUpdater(cur,'dbconfig',configConversion='configConversion')
    s = {}
    dbu(s)
    for k,v,conv,x in dbData:
      assert x == s[k], 'Expected type %s: "%s", got type: %s: "%s"'%(type(x),x,type(s[k]),s[k])

  def testConstructor(self):
    internals = set(cm.getDefaultedConfigOptions().keys())
    internals.update(['configurationModule','updateDelta','updateInterval','updateFunction','reEvaluateFunction','signalNumber'])
    markers = []
    def mark(conf):
      markers.append(datetime.datetime.now())
    kwargss = [
      ({'configurationModule':dyConfig,
       #'updateInterval':'0',
       #'updateFunction':noop,
       'reEvaluateFunction':mark,
       'signalNumber':0,
       },
       {'updateDelta':datetime.timedelta(0),
        'updateFunction':dcm.noop,
        'reEvaluateFunction':mark,
        'signalNumber':0,
        'testOption0':0,
        'testOption1':'one',
        'logFilePathname':'/some/bogus/location',
        'markCount':1,
        }, 0),
      
      ({'configurationModule':dyConfig,
       'updateInterval':'10:0',
       #'updateFunction':mark,
       #'reEvaluateFunction':mark,
       #'signalNumber':0,
       },
       {'updateDelta':datetime.timedelta(minutes=10),
        'updateFunction':dcm.noop,
        'reEvaluateFunction':dcm.noop,
        'signalNumber':14,
        'testOption0':0,
        'testOption1':'one',
        'logFilePathname':'/some/bogus/location',
        'markCount':0,
        },1),
      
       ({'configurationModule':dyConfig,
       #'updateInterval':0,
       'updateFunction':mark,
       'reEvaluateFunction':mark,
       'signalNumber':11,
       },
       {'updateDelta':datetime.timedelta(0),
        'updateFunction':mark,
        'reEvaluateFunction':mark,
        'signalNumber':11,
        'testOption0':0,
        'testOption1':'one',
        'logFilePathname':'/some/bogus/location',
        'markCount':2,
        },2),
      ]
    for args,expected,loop in kwargss:
      topTime = datetime.datetime.now()
      tdcm = dcm.DynamicConfig(**args)
      for k in expected:
        inside = k in internals
        if not k == 'markCount':
          if inside:
            assert expected[k] == getattr(tdcm.internal,k),'Loop %s: Expected %s, got %s'%(loop,expected[k],getattr(tdcm.internals,k))
          else:
            assert expected[k] == tdcm[k],'Loop %s: Expected %s, got %s'%(loop,expected[k],tdcm[k])
        else:
          if expected['markCount']:
            now = datetime.datetime.now()
            assert expected['markCount'] == len(markers), 'Loop %s: Expected %d, got %d'%(loop,expected['markCount'], len(markers))
            for m in markers:
              assert topTime < m, 'Loop %s: But topTime: %s, and %s'%(topTime,markers)
              assert m < now, 'Loop %s: But %s and now: %s'%(loop,markers,now)
      del(markers[:])

  def testCloseEtc(self):
    """testDynamicConfigurationManager:TestDynamicConfigurationManager.testClose
    Actually checking that multiple constructors followed by calls to close() have expected behavior
    """
    tcdms = []
    reload(dcm)
    for i in range(5):
      tcdms.append(dcm.DynamicConfig())
      assert len(tcdms) == len(dcm.DynamicConfig.instances),'but at loop %d: tcdms=%d versus dcmInst %d'%(i,len(tcdms),len(dcm.DynamicConfig.instances))
    expectedLen = 5
    for i in [3,0,2,1,4]: # some twisty order or other
      assert id(tcdms[i]) in dcm.DynamicConfig.instances
      assert expectedLen == len(dcm.DynamicConfig.instances)
      tcdms[i].close()
      expectedLen -= 1
      assert id(tcdms[i]) not in dcm.DynamicConfig.instances
      assert expectedLen == len(dcm.DynamicConfig.instances)
      
  def testItemAccess(self):
    """testDynamicConfigurationManager:TestDynamicConfigurationManager.testItemAccess (slow=2.5)"""
    markers = []
    def mark(conf):
      markers.append(datetime.datetime.now())
    tcdm = dcm.DynamicConfig(configurationModule=dyConfig,updateFunction=mark,updateInterval='0:1')
    del(markers[:])
    value = tcdm['testOption0']
    assert [] == markers
    time.sleep(.2)
    value = tcdm['testOption0']
    assert 0 == len(markers)
    time.sleep(.3)
    value = tcdm['testOption0']
    assert 0 == len(markers)
    time.sleep(.6)
    value = tcdm['testOption0']
    assert 1 == len(markers)
    time.sleep(1.1)
    value = tcdm['testOption0']
    assert 2 == len(markers)

  def testAttrAccess(self):
    """testDynamicConfigurationManager:TestDynamicConfigurationManager.testAttrAccess (slow=2.5)"""
    markers = []
    def mark(conf):
      markers.append(datetime.datetime.now())
    tcdm = dcm.DynamicConfig(configurationModule=dyConfig,updateFunction=mark,updateInterval='0:1')
    tcdm['aVal'] = 'yet again'
    del(markers[:])
    value = tcdm.aVal
    assert [] == markers
    time.sleep(.2)
    value = tcdm.aVal
    assert 0 == len(markers)
    time.sleep(.3)
    value = tcdm.aVal
    assert 0 == len(markers)
    time.sleep(.6)
    value = tcdm.aVal
    assert 1 == len(markers)
    time.sleep(1.1)
    value = tcdm.aVal
    assert 2 == len(markers)

    # def testGet(self):
      # pass # too simple to bother testing, but did anyway in testHandleAlarm

  # def testMaybeUpdate(self):
    # pass # Done in testItemAccess and testAttrAccess

  def testDoUpdate(self):
    markers = []
    def mark(conf):
      markers.append(datetime.datetime.now())
    tcdm = dcm.DynamicConfig(configurationModule=dyConfig,updateFunction=mark,reEvaluateFunction=mark)
    del(markers[:])
    tcdm.doUpdate()
    assert 2 == len(markers)
      
