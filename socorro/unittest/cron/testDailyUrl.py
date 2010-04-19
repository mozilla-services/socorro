import unittest

import csv
import datetime as dt
import gzip
import os
import psycopg2 as pg
import shutil
import simplejson
import sys
import time

import socorro.lib.filesystem as soc_filesys
import socorro.database.schema as soc_schema
import socorro.database.postgresql as soc_pg
import socorro.lib.dynamicConfigurationManager as configManager
import socorro.database.database as sdatabase

import socorro.unittest.testlib.util as tutil
import socorro.unittest.testlib.loggerForTest as tLogger

import socorro.unittest.config.commonconfig as commonconfig

import socorro.cron.dailyUrl as dailyUrl

logger = tLogger.TestingLogger()
dailyUrl.logger = logger

productData = {
  # 'reports': [[id,signature,url,client_crash_date,date_processed,product,version,email,topmost_filenames,addons_checked,flash_version], ...]
  # 'bug_associations':[[bug_id,signature], ...]
  # 'productdims': [[id,product,version,branch], ...],
  'order':['bugs','reports','productdims','bug_associations'],
  'reports': {
  'cols': 'id,signature,url,uuid,client_crash_date,date_processed,product,version,uptime,email,topmost_filenames,addons_checked,flash_version,hangid,reason',
  'data': [
    [1,'signature0','abc','abcd289c-a4e0-496a-a120-beb6d2101225','2010-12-25T12:04:00','2010-12-25T12:04:05','fire','1.2.3',120,'0b.c','file0',True,'FV10.0.1',None,'I said so'],
    [2,'signature0','def','abcd289c-a4e0-496a-a121-beb6d2101225','2010-12-25T12:01:00','2010-12-25T12:01:02','fire','1.2.4',121,'1@b.c','file0',None,'FV10.0.1',None,None],
    [3,'signature0','ghi','abcd289c-a4e0-496a-a122-beb6d2101225','2010-12-25T12:02:00','2010-12-25T12:02:03','fire','1.2.3',122,'2@b.c','file0',False,'FV10.0.1',None,None],
    [4,'signature1',None, 'abcd289c-a4e0-496a-a123-beb6d2101225','2010-12-25T12:03:00','2010-12-25T12:03:04','bird','1.0.0',123,'f**kU','file1',True,'FV10.1.1',None,None],
    [5,'signature1','jkl','abcd289c-a4e0-496a-a124-beb6d2101225','2010-12-25T12:00:00','2010-12-25T12:00:01','bird','1.0.0',124,'4@b.c','file1',True,'FV10.1.1','bogus crash id',None],
    [6,'signature2','mmm','abcd289c-a4e0-496a-a125-beb6d2101225','2010-12-25T12:05:00','2010-12-25T12:05:06','fire','1.2.3',125,'5@b.c','file1',True,'FV10.1.1','bogus crash id',None],
  ],
    },
  'bugs': {
  'data': [[12345,'open','testbug 12345'],[12346,'closed','testbug 12346'],[12347,'open','testbug 12347']],
  'cols': 'id,status,short_desc'
  },
  'bug_associations':{
  'data': [[12345,'signature0'],[12346,'signature0'],[12347,'signature1']],
  'cols': 'bug_id,signature',
  },
  'productdims': {
  'data': [[1,'fire','1.2.3','b3'],[2,'fire','1.2.4','b4'],[3,'bird','1.0.0','b0']],
  'cols': 'id,product,version,branch',
  },
  }

expectedPrivate = [
  'signature	url	uuid_url	client_crash_date	date_processed	last_crash	product	version	build	branch	os_name	os_version	cpu_name	address	bug_list	user_comments	uptime_seconds	email	adu_count	topmost_filenames	addons_checked	flash_version	hangid	reason',
  'signature1	jkl	http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a124-beb6d2101225	201012251200	201012251200	\N	bird	1.0.0	\N	b0	\N	\N	\N	\N	12347	\N	124	yes	\N	file1	checked	FV10.1.1	bogus crash id	\N',
  'signature0	def	http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a121-beb6d2101225	201012251201	201012251201	\N	fire	1.2.4	\N	b4	\N	\N	\N	\N	12345,12346	\N	121	yes	\N	file0	[unknown]	FV10.0.1	\N	\N',
  'signature0	ghi	http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a122-beb6d2101225	201012251202	201012251202	\N	fire	1.2.3	\N	b3	\N	\N	\N	\N	12345,12346	\N	122	yes	\N	file0	not	FV10.0.1	\N	\N',
  'signature1	\N	http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a123-beb6d2101225	201012251203	201012251203	\N	bird	1.0.0	\N	b0	\N	\N	\N	\N	12347	\N	123		\N	file1	checked	FV10.1.1	\N	\N',
  'signature0	abc	http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a120-beb6d2101225	201012251204	201012251204	\N	fire	1.2.3	\N	b3	\N	\N	\N	\N	12345,12346	\N	120		\N	file0	checked	FV10.0.1	\N	I said so',
  'signature2	mmm	http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a125-beb6d2101225	201012251205	201012251205	\N	fire	1.2.3	\N	b3	\N	\N	\N	\N		\N	125	yes	\N	file1	checked	FV10.1.1	bogus crash id	\N',
  ]

expectedPublic = [
  "signature	URL (removed)	uuid_url	client_crash_date	date_processed	last_crash	product	version	build	branch	os_name	os_version	cpu_name	address	bug_list	user_comments	uptime_seconds		adu_count	topmost_filenames	addons_checked	flash_version	hangid	reason",
  "signature1	URL (removed)	http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a124-beb6d2101225	201012251200	201012251200	\N	bird	1.0.0	\N	b0	\N	\N	\N	\N	12347	\N	124		\N	file1	checked	FV10.1.1	bogus crash id	\N",
  "signature0	URL (removed)	http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a121-beb6d2101225	201012251201	201012251201	\N	fire	1.2.4	\N	b4	\N	\N	\N	\N	12345,12346	\N	121		\N	file0	[unknown]	FV10.0.1	\N	\N",
  "signature0	URL (removed)	http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a122-beb6d2101225	201012251202	201012251202	\N	fire	1.2.3	\N	b3	\N	\N	\N	\N	12345,12346	\N	122		\N	file0	not	FV10.0.1	\N	\N",
  "signature1	URL (removed)	http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a123-beb6d2101225	201012251203	201012251203	\N	bird	1.0.0	\N	b0	\N	\N	\N	\N	12347	\N	123		\N	file1	checked	FV10.1.1	\N	\N",
  "signature0	URL (removed)	http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a120-beb6d2101225	201012251204	201012251204	\N	fire	1.2.3	\N	b3	\N	\N	\N	\N	12345,12346	\N	120		\N	file0	checked	FV10.0.1	\N	I said so",
  "signature2	URL (removed)	http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a125-beb6d2101225	201012251205	201012251205	\N	fire	1.2.3	\N	b3	\N	\N	\N	\N		\N	125		\N	file1	checked	FV10.1.1	bogus crash id	\N",
]

def setup_module():
  tutil.nosePrintModule(__file__)

class TestFormatter:
  def __init__(self,initialData = []):
    self.data = initialData

  def writerow(self,aList):
    self.data.append(aList)

class TestDailyUrl(unittest.TestCase):
  def setUp(self):
    self.outDir = os.path.join(os.path.split(__file__)[0],'Outdir')
    self.config = configManager.newConfiguration(configurationModule=commonconfig, applicationName='Test DailyUrl')
    self.connection = sdatabase.Database(self.config).connection()
    #dsn = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % self.config
    #self.connection = pg.connect(dsn)
    cursor = self.connection.cursor()
    # First clean, just in case
    try:
      soc_schema.teardownDatabase(self.config,logger)
    except:
      pass
    try:
      shutil.rmtree(self.outDir)
    except:
      pass
    # Now create
    soc_filesys.makedirs(self.outDir)
    soc_schema.setupDatabase(self.config,logger)
    for k in productData['order']:
      placeholders = ', '.join(['%s' for x in productData[k]['data'][0]])
      sql = 'INSERT INTO %s (%s) VALUES (%s)'%(k,productData[k]['cols'],placeholders)
      cursor.executemany(sql,productData[k]['data'])
      self.connection.commit()

  def tearDown(self):
    #print logger
    try:
      soc_schema.teardownDatabase(self.config,logger)
    except:
      pass
    try:
      shutil.rmtree(self.outDir)
    except Exception,x:
      assert 0,"Failure to tearDown: %s"%(x)

  def testDailyUrlDump_noPublic(self):
    logger.clear()
    #self.config['publicOutputPath'] = self.outDir
    self.config['outputPath'] = self.outDir
    self.config['day'] = dt.date(2010,12,25)
    dailyUrl.dailyUrlDump(self.config)
    outFiles = os.listdir(self.outDir)
    assert 1 == len(outFiles), 'but got: "%s"'%(os.listdir(self.outDir))
    assert '20101225-crashdata.csv.gz' in outFiles, 'but got: "%s"'%(os.listdir(self.outDir))
    zipFile = gzip.open(os.path.join(self.outDir,'20101225-crashdata.csv.gz'),'r')
    lines = []
    line = zipFile.readline().strip()
    while line:
      lines.append(line)
      line = zipFile.readline().strip()
    assert len(expectedPrivate) == len(lines), 'expected: %s\ngot:     %s'%(expectedPrivate,lines)
    for i in range(len(lines)):
      assert expectedPrivate[i] == lines[i], '%d:\nExpected: %s\ngot:     %s'%(i,expectedPrivate[i],lines[i])

  def testDailyUrlDump_withPublic(self):
    logger.clear()
    self.config['publicOutputPath'] = self.outDir
    self.config['outputPath'] = self.outDir
    self.config['day'] = dt.date(2010,12,25)
    dailyUrl.dailyUrlDump(self.config)
    outFiles = os.listdir(self.outDir)
    assert 2 == len(outFiles), 'but got: "%s"'%(os.listdir(self.outDir))
    assert '20101225-pub-crashdata.csv.gz' in outFiles, 'but got: "%s"'%(os.listdir(self.outDir))
    zipFile = gzip.open(os.path.join(self.outDir,'20101225-pub-crashdata.csv.gz'),'r')
    lines = []
    line = zipFile.readline().strip()
    while line:
      lines.append(line)
      line = zipFile.readline().strip()
    assert len(expectedPublic) == len(lines), 'expected: %s\ngot:     %s'%(expectedPublic,lines)
    for i in range(len(lines)):
      assert expectedPublic[i] == lines[i], '%d:\nExpected: %s\ngot:     %s'%(i,expectedPublic[i],lines[i])


  def testWriteRowToInternalAndExternalFiles(self):
    iF = TestFormatter([])
    pF = TestFormatter([])
    data = [
      ['0','http://url',2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'email@a.b',18],
      ['0','', 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'', 18],
      ['0','', 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'email@a.b',18],
      ]
    iExpected = [
      ['0','http://url',2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'email@a.b',18],
      ['0','', 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'', 18],
      ['0','', 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'email@a.b',18],
      ]
    pExpected = [
      ['0','URL (removed)',2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'',18],
      ['0','', 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'', 18],
      ['0','', 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'',18],
      ]
    for d in data:
      dailyUrl.writeRowToInternalAndExternalFiles(iF,pF,d)

    for i in range(len(iF.data)):
      assert iExpected[i] == iF.data[i]
    for i in range(len(pF.data)):
      assert pExpected[i] == pF.data[i]

