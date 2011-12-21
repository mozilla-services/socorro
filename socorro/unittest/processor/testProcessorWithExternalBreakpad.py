import unittest

import socorro.processor.externalProcessor as xp

class SignatureUtilities(object):
    def generate_signature_from_list(self, sig_list, hangType):
        return sig_list[0]

class TestExternalProcessor(xp.ProcessorWithExternalBreakpad):
    def __init__(self):
        # skipping parent class initialization
        self.signatureUtilities = SignatureUtilities()

class TestCase(unittest.TestCase):
    def test_generate_signature_1(self):
        p = TestExternalProcessor()
        signature_list = [ 'a', 'b', 'c' ]
        app_notes = ''
        hang_type = 0
        crashed_thread = 0
        processor_notes_list = []
        sig = p.generate_signature(signature_list,
                                   app_notes,
                                   hang_type,
                                   crashed_thread,
                                   processor_notes_list)
        assert sig == 'a'

    def test_generate_signature_2(self):
        p = TestExternalProcessor()
        signature_list = [ xp.java_signature_sentinel, 'b', 'c' ]
        app_notes = 'java signature {thrilling, eh?}'
        hang_type = 0
        crashed_thread = 0
        processor_notes_list = []
        sig = p.generate_signature(signature_list,
                                   app_notes,
                                   hang_type,
                                   crashed_thread,
                                   processor_notes_list)
        assert sig == 'java signature'

    def test_generate_signature_3(self):
        p = TestExternalProcessor()
        signature_list = [ xp.java_signature_sentinel, 'b', 'c' ]
        app_notes = 'java signature'*100
        hang_type = 0
        crashed_thread = 0
        processor_notes_list = []
        sig = p.generate_signature(signature_list,
                                   app_notes,
                                   hang_type,
                                   crashed_thread,
                                   processor_notes_list)
        assert sig == 'EMPTY: java stack not in expected format'

    def test_generate_signature_4(self):
        p = TestExternalProcessor()
        signature_list = [ xp.java_signature_sentinel, 'b', 'c' ]
        app_notes = 'java signature'*100 + '{'
        hang_type = 0
        crashed_thread = 0
        processor_notes_list = []
        sig = p.generate_signature(signature_list,
                                   app_notes,
                                   hang_type,
                                   crashed_thread,
                                   processor_notes_list,
                                   signature_max_len=17)
        assert sig == 'java signature...'




# This entire file needs to be rewritten to not depend on ProcessedDumpStorage and JsonDumpStorage
## 1 (KEEP THESE as first two lines in file: Used for a test)
## 2 (KEEP THESE as first two lines in file: Used for a test)
#"""
#You must run this test module using nose (chant nosetests from the command line)
#** There are some issues with nose, offset by the fact that it does multi-thread and setup_module better than unittest
 #* This is NOT a unittest.TestCase ... it could be except that unittest screws up setup_module
 #* nosetests may hang in some ERROR conditions. SIGHUP, SIGINT and SIGSTP are not noticed. SIGKILL (-9) works
 #* You should NOT pass command line arguments to nosetests. You can pass them, but it causes trouble:
 #*   Nosetests passes them into the test environment which breaks socorro's configuration behavior
 #*   You can set NOSE_WHATEVER envariables prior to running if you need to. See nosetests --help
 #*    some useful envariables:
 #*      NOSE_VERBOSE=x where x in [0,      # Prints only 'OK' at end of test run
 #*                                 1,      # default: Prints one '.' per test like unittest
 #*                                 x >= 2, # Prints first comment line if exists, else the function name per test
 #*                                ]
 #*      NOSE_WHERE=directory_path[,directoroy_path[,...]] : run only tests in these directories. Note commas
 #*      NOSE_ATTR=attrspec[,attrspec ...] : run only tests for which at least one attrspec evaluates true.
 #*         Accepts '!attr' and 'attr=False'. Does NOT accept natural python syntax ('atter != True', 'not attr')
 #*      NOSE_NOCAPTURE=TrueValue : nosetests normally captures stdout and only displays it if the test has fail or error.
 #*         print debugging works with this envariable, or you can instead print to stderr or use a logger
 #*
 #* With NOSE_VERBOSE > 1, you may see "functionName(self): (slow=N)" for some tests. N is the max seconds waiting
#"""
#import copy
#import datetime as dt
#import errno
#import logging
#import os
#import os.path
#import shutil
#import sys
#import time

#import psycopg2
#from nose.tools import *

#import socorro.lib.ConfigurationManager as configurationManager
#import socorro.lib.util as libutil
#import socorro.processor.externalProcessor as eProcessor
#import socorro.processor.processor as processor
#import socorro.database.schema as schema
#import socorro.database.database as sdatabase
#import socorro.lib.filesystem as filesystem


#import socorro.unittest.testlib.createJsonDumpStore as createJDS
#import socorro.unittest.testlib.dbtestutil as dbtestutil
#from   socorro.unittest.testlib.loggerForTest import TestingLogger
#from   socorro.unittest.testlib.testDB import TestDB
#import socorro.unittest.testlib.util as tutil

#import processorTestconfig as testConfig

#class Me: # not quite "self"
  #"""
  #I need stuff to be initialized once per module. Rather than having a bazillion globals, lets just have 'me'
  #"""
  #pass
#me = None

#def setup_module():
  #global me
  #if me:
    #return
  ## else initialize
  #me = Me()
  #me.testDB = TestDB()
  ## the next line is redundant with the same line in TestProcessorWithExternalBreakPad.setUp(). Deliberately.
  #me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing Processor')
  #tutil.nosePrintModule(__file__)
  #myDir = os.path.split(__file__)[0]
  #if not myDir: myDir = '.'
  #replDict = {'testDir':'%s'%myDir}
  #for i in me.config:
    #try:
      #me.config[i] = me.config.get(i)%(replDict)
    #except:
      #pass
  #eProcessor.logger.setLevel(logging.DEBUG)
  #me.logFilePathname = me.config.logFilePathname
  #logfileDir = os.path.split(me.config.logFilePathname)[0]
  #try:
    #os.makedirs(logfileDir)
  #except OSError,x:
    #if errno.EEXIST != x.errno: raise
  #f = open(me.config.logFilePathname,'w')
  #f.close()
  #fileLog = logging.FileHandler(me.logFilePathname, 'a')
  #fileLog.setLevel(logging.DEBUG)
  #fileLogFormatter = logging.Formatter(me.config.logFileLineFormatString)
  #fileLog.setFormatter(fileLogFormatter)
  #eProcessor.logger.addHandler(fileLog)
  #me.logger = TestingLogger(eProcessor.logger)
  ##me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      ##me.config.databaseUserName,me.config.databasePassword)
  #me.database = sdatabase.Database(me.config)
  #try:
    #filesystem.makedirs(me.config.processedDumpStoragePath) #create place for processed Dumps to go
  #except OSError, x:
    #assert False, "cannot setup processedDumpStoragePath: %s" % x
  #assert os.path.exists(me.config.processedDumpStoragePath), "the processed dump path is missing: %s" % me.config.processedDumpStoragePath

#def teardown_module():
  #global me
  #logging.shutdown()
  #try:
    #os.unlink(me.logFilePathname)
  #except OSError,x:
    #if errno.ENOENT != x.errno:
      #raise

#class TestProcessorWithExternalBreakpad:
  #def setUp(self):
    #global me
    #eProcessor.logger = me.logger
    #me.logger.clear()
    #me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing Processor')
    #myDir = os.path.split(__file__)[0]
    #if not myDir: myDir = '.'
    #replDict = {'testDir':'%s'%myDir}
    #for i in me.config:
      #try:
        #me.config[i] = me.config.get(i)%(replDict)
      #except:
        #pass

    ## clean out the old storage, just in case
    #try:
      #shutil.rmtree(me.config.storageRoot)
    #except OSError:
      #pass # ok if there is no such test directory
    #try:
      #shutil.rmtree(me.config.deferredStorageRoot)
    #except OSError:
      #pass # ok if there is no such test directory
    #try:
      #os.makedirs(me.config.storageRoot)
    #except OSError, x:
      #if errno.EEXIST == x.errno: pass
      #else: raise
    #try:
      #os.makedirs(me.config.deferredStorageRoot)
    #except OSError,x:
      #if errno.EEXIST == x.errno: pass
      #else: raise
    #try:
      #os.makedirs(me.config.processedDumpStoragePath)
    #except OSError,x:
      #if errno.EEXIST == x.errno: pass
      #else: raise

    ## create a useful database connection, and use it
    #self.connection = me.database.connection()
    ##self.connection = psycopg2.connect(me.dsn)
    #me.testDB.removeDB(me.config,me.logger)
    #schema.partitionCreationHistory = set() # an 'orrible 'ack
    #me.testDB.createDB(me.config,me.logger)

  #def tearDown(self):
    #global me
    #me.testDB.removeDB(me.config,me.logger)
    #try:
      #shutil.rmtree(me.config.storageRoot)
    #except OSError:
      #pass # ok if there is no such test directory
    #try:
      #shutil.rmtree(me.config.deferredStorageRoot)
    #except OSError:
      #pass # ok if there is no such test directory
    #try:
      #shutil.rmtree(me.config.processedDumpStoragePath)
    #except OSError:
      #pass # ok if there is no such test directory

  #def testConstructor(self):
    #"""
    #TestProcessorWithExternalBreakpad.testConstructor(self):
      #Constructor must fail if any of the necessary configuration details are missing
      #commandLine must be appropriately constructed based on config and rules
    #"""
    #global me
    #requiredConfigs = [
      #"processorSymbolsPathnameList",
      #"crashingThreadFrameThreshold",
      #"crashingThreadTailFrameThreshold",
      #"stackwalkCommandLine",
      #]
    #cc = copy.copy(me.config)
    #for rc in requiredConfigs:
      #del(cc[rc])
      #assert_raises(AssertionError,eProcessor.ProcessorWithExternalBreakpad,cc)
      ## super.__init__() is called before our failure: Creates an entry in the processors table
      ## that entry causes a spurious (non-unique name) failure on the next cycle, so erase it:
      #self.connection.cursor().execute("DELETE FROM processors")
      #self.connection.commit()
    #me.config['stackwalkCommandLine'] = '$one -a$(two) -b $(dumpfilePathname) -s$processorSymbolsPathnameList'
    #me.config['one'] = 'ONE'
    #me.config['two'] = 'TWO'
    #p = eProcessor.ProcessorWithExternalBreakpad(me.config)
    #expected = 'ONE -aTWO -b DUMPFILEPATHNAME -sSYMBOL_PATHS'
    #assert expected == p.commandLine, 'Expected "%s" got "%s"'%(expected,p.commandLine)

  #def getExe(self,possibleNames):
    #"""attempt to find a particular executable along users PATH
    #possibleNames: a list of choices (e.g: ['cat', 'head -2'])
    #each name is split() and only the first token is used.
    #for each possible name, look in each possible PATH directory until success
    #return actual path to full name else None
    #"""
    #for fullName in possibleNames:
      #name = fullName.split()[0]
      #for i in os.environ.get('PATH','').split(os.path.pathsep):
        #if os.access(os.path.join(i,name),os.X_OK):
          #return os.path.join(i,fullName)
    #return None

  #def testInvokeBreakpadStackdump(self):
    #"""
    #TestProcessorWithExternalBreakpad.testInvokeBreakpadStackdump(self):
      #check that we get file-type iterator (using /bin/cat instead of the actual breakpad tool)
      #check that the symbol paths and dumpfilepathname are appropriately fixed up (using /bin/echo )
    #"""
    #global me
    #catExe = self.getExe(['cat','head -2'])
    #assert catExe, "Cannot run this test without a 'cat-like' command"
    #p = eProcessor.ProcessorWithExternalBreakpad(me.config)
    #p.commandLine = '%s DUMPFILEPATHNAME'%catExe
    #getter,handle = p.invokeBreakpadStackdump(__file__.replace('pyc','py'))
    #topLineTemplate = "# %s (KEEP THESE as first two lines in file: Used for a test)"
    #i = 1
    #for line in getter:
      #assert topLineTemplate%(i) == line.strip(),'Expected "%s" got "%s"'%(topLineTemplate%(i),line)
      #if i >= 2: break
      #i += 1
    #for line in getter: # use up all the lines in the file, so as to...
      #pass # ... avoid seeing this on stderr after the test: 'cat: stdout: Broken pipe'
    #echoExe = self.getExe(['echo'])
    #assert echoExe, "Cannot run this test without an 'echo' command"
    #expected = 'one two three target'
    #p.commandLine = '%s SYMBOL_PATHS DUMPFILEPATHNAME'%(echoExe)
    #p.config['processorSymbolsPathnameList'] = "one     two\tthree"
    #getter,handle = p.invokeBreakpadStackdump('target')
    #for line in getter:
      #assert expected == line.strip(), 'Expected "%s" got "%s"'%(expected,line)
    #p.config['processorSymbolsPathnameList'] = ["one", "two","three"]
    #getter,handle = p.invokeBreakpadStackdump('target')
    #for line in getter:
      #assert expected == line.strip(), 'Expected "%s" got "%s"'%(expected,line)

  #def testAnalyzeHeader(self):
    #"""
    #TestProcessorWithExternalBreakpad.testAnalyzeHeader(self):
      #check that missing header is correctly diagnosed and handled
      #check that empty line break after header is noticed and nothing after is parsed
      #check that badly formatted header lines are appropriately diagnosed and handled
      #check that correctly formatted header lines are seen and appropriately parsed,
        #- including empty fields
        #- including missing CrashedThread
      #check that database is correctly updated (or not)
      #check for correct return value
    #"""
    #global me
    #p = eProcessor.ProcessorWithExternalBreakpad(me.config)
    #con,cur = p.databaseConnectionPool.connectionCursorPair()
    #id = 1
    #data = dbtestutil.makeJobDetails({1:1})
    #uuid = data[0][1]
    #createJDS.createTestSet({uuid:createJDS.jsonFileData[uuid]},{'logger':me.logger},p.config.storageRoot)
    #path = p.jsonPathForUuidInJsonDumpStorage(uuid)
    #product = 'bogus'
    #version = '3.xBogus'
    #buildId = '1966060622'
    #nowstamp = time.time()
    #now = dt.datetime.fromtimestamp(nowstamp)
    #processDate = now
    #crashTime = "%d"%(nowstamp - 10000)
    #jsonDoc = {'ProductName':product,'Version':version,'BuildID':buildId,'CrashTime':crashTime}
    #dbFields = ["date_processed","uuid","cpu_name","cpu_info","reason","address","product", "version","os_name"]
    #selectSql = 'SELECT %s FROM reports WHERE id=%%s'%(','.join(dbFields))
    #p.insertReportIntoDatabase(cur,uuid,jsonDoc,path,now,[])
    ## get the initial state of the data
    #cur.execute(selectSql,(id,))
    #con.commit()
    #beforeData = cur.fetchall()

    ## check that we behave as expected for no header (no db update, two messages)
    #messages = []
    #result = p.analyzeHeader(id,iter(['\n']),cur,processDate,messages)
    #con.commit() # because analyzeHeader should not do it
    #cur.execute(selectSql,(id,))
    #con.commit()
    #afterData = cur.fetchall()
    #for i in range(len(beforeData[0])):
      #assert beforeData[0][i] == afterData[0][i], 'Column %s: Expected %s, got %s'%(dbFields[i],beforeData[0][i],afterData[0][i])
    #assert None == result["crashedThread"]
    #assert 2 == len(messages), "Expected two messages, got %s"%(str(messages))
    #assert 'returned no header lines for reportid: %s'%id in messages[0],'Got %s'%(messages[0])
    #assert 'No thread' in messages[1], 'Expected "no thread was identified as the cause of the crash", got "%s"'%(messages[1])
    #assert 'cause of the crash' in messages[1], 'Expected "No thread was identified as the cause of the crash", got "%s"'%(messages[1])

    ## check that we see only stuff before header break
    #messages = []
    #beforeData = cur.fetchall()
    #result = p.analyzeHeader(id,iter(['OS|osName|osVersion|','\n','CPU|cpuName|cpuInfo','\n']),cur,processDate,messages)
    #expected = [processDate,uuid,None,None,None,None,'bogus','3.xBogus','osName']
    #assert None == result["crashedThread"],'Expected None crashedThread returned, got %s'%result
    #cur.execute(selectSql,(id,))
    #con.commit()
    #afterData = cur.fetchall()

    #for i in range(len(afterData[0])):
      #ex = expected[i]
      #ad = afterData[0][i]
      #assert ex == ad,  'Column %s: Expected %s, got %s'%(dbFields[i],ex,ad)
    #assert 1 == len(messages), "Expected just one message, got %s"%(str(messages))
    #assert 'No thread' in messages[0], 'Expected "no thread was identified as the cause of the crash", got "%s"'%(messages[0])
    #assert 'cause of the crash' in messages[0], 'Expected "no thread was identified as the cause of the crash", got "%s"'%(messages[0])

    ## check that we appropriately handle too few or empty string items in header lines
    #cur.execute('update reports set cpu_name=%s,cpu_info=%s,product=%s,version=%s,os_name=%s,reason=%s,address=%s where id=%s',(None,None,None,None,None,None,None,id))
    #cur.execute(selectSql,(id,))
    #con.commit()
    #beforeData = cur.fetchall()
    #messages = []
    #testData = ['OS|osVersion','CPU|cpuName','Crash|oopsy','\n']
    #result = p.analyzeHeader(id,iter(testData),cur,processDate,messages)
    #con.commit() # because analyzeHeader should not do it
    #assert None == result["crashedThread"], 'Expect no result, short crash data'
    #cur.execute(selectSql,(id,))
    #con.commit()
    #afterData = cur.fetchall()
    #for i in range(len(beforeData[0])):
      #bd = beforeData[0][i]
      #ad = afterData[0][i]
      #if i > 1:
        #assert None == ad,'Expected no change from None, but at %s: "%s"'%(dbFields[i],ad)
      #assert bd == ad,'Expected no change from "%s" but at %s: "%s"'%(bd,dbFields[i],ad)
    #assert 4 == len(messages), 'Every field was short by at least one datum, but %s'%(str(messages))
    #for i in range(len(messages)):
      #if i < 3:
        #assert 'Cannot parse header line "' in messages[i]
        #assert testData[i] in messages[i]
      #else:
        #assert 'No thread' in messages[i], 'Expected "No thread was identified as the cause of the crash", got "%s"'%(messages[i])
        #assert 'cause of the crash' in messages[i], 'Expected "No thread was identified as the cause of the crash", got "%s"'%(messages[i])

    ## check that we appropriately handle badly formatted header line
    #cur.execute('update reports set cpu_name=%s,cpu_info=%s,product=%s,version=%s,os_name=%s,reason=%s,address=%s where id=%s',(None,None,None,None,None,None,None,id))
    #cur.execute(selectSql,(id,))
    #con.commit()
    #beforeData = cur.fetchall()
    #messages = []
    #testData = ['OS|osName|osVersion|||\n','CPU |cpuName | cpuVersion\n','Crash|oopsy|0xdeadbeef|tid\n','\n']
    #expected = [None,None,'cpuName','cpuVersion','oopsy','0xdeadbeef',None,None,'osName']
    #result = p.analyzeHeader(id,iter(testData),cur,processDate,messages)
    #con.commit() # because analyzeHeader should not do it
    #assert None == result["crashedThread"]
    #cur.execute(selectSql,(id,))
    #con.commit()
    #afterData = cur.fetchall()
    #con.commit()
    #for i in range(2,len(beforeData[0])):
      #bd = beforeData[0][i]
      #ad = afterData[0][i]
      #assert str(ad) == str(ad).strip(), 'Expect no surrounding white space on data, but at %i: [%s]'%(dbFields[i],ad)
      #if not dbFields[i] in ['product', 'version']:
        #assert bd != ad, 'Expected None=>new value, but for %s, got %s'%(dbFields[i],ad)
      #assert expected[i] == ad, 'Expected %s, got %s'%(expected[i],ad)
    #assert 1 == len(messages), 'Expected "No thread was identified" but %s'%(str(messages))
    #assert 'No thread' in messages[0], 'Expected "No thread was identified as the cause of the crash", got "%s"'%(messages[0])
    #assert 'cause of the crash' in messages[0], 'Expected "No thread was identified as the cause of the crash", got "%s"'%(messages[0])
    ## check that "too much but ok" lines are correctly parsed
    #cur.execute('update reports set cpu_name=%s,cpu_info=%s,os_name=%s,reason=%s,address=%s where id=%s',(None,None,None,None,None,id))
    #cur.execute(selectSql,(id,))
    #con.commit()
    #beforeData = cur.fetchall()
    #messages = []
    #testData = ['CPU|cpuName | cpuVersion||\n','OS|AnOsName|AnOsVersion|osSubVersion\n',"BAD|IDEA\n",'Crash||0xdeadbeef|66|77|88','\n']
    #expected = [processDate,uuid,'cpuName','cpuVersion',None,'0xdeadbeef',None,None,'AnOsName']
    #result = p.analyzeHeader(id,iter(testData),cur,processDate,messages)
    #con.commit() # because analyzeHeader should not do it
    #assert 66 == result["crashedThread"]
    #cur.execute(selectSql,(id,))
    #con.commit()
    #afterData = cur.fetchall()
    #for i in range(len(beforeData[0])):
      #bd = beforeData[0][i]
      #ad = afterData[0][i]
      #assert str(ad) == str(ad).strip(), 'Expect no surrounding white space on data, but at %s: [%s]'%(dbFields[i],ad)
      #if i > 1 and expected[i]:
        #assert bd != ad, 'Expected None=>new value, but for %s, got %s=>%s'%(dbFields[i],bd,ad)
      #assert expected[i] == ad, 'At %s expected %s, got %s'%(dbFields[i],expected[i],ad)
    #assert 1 == len(messages), 'Expect unparseable "BAD|IDEA", but got %s'%(str(messages))
    #assert 'Cannot parse header line' in messages[0], "but %s"%(messages[0])
    #assert 'BAD|IDEA' in messages[0], "but %s"%(messages[0])

  #def testAnalyzeFrames_Plain(self):
    #"""
    #TestProcessorWithExternalBreakpad.testAnalyzeFrames_Plain(self):
      #check that we get the expected cache, database entries with no messages for a 'plain jane' call
    #"""
    #global me
    #p = eProcessor.ProcessorWithExternalBreakpad(me.config)
    #p.config['crashingThreadFrameThreshold'] = 15
    #con,cur = p.databaseConnectionPool.connectionCursorPair()
    #data = dbtestutil.makeJobDetails({1:1})
    #uuid = data[0][1]
    #createJDS.createTestSet({uuid:createJDS.jsonFileData[uuid]},{'logger':me.logger},p.config.storageRoot)
    #path = p.jsonPathForUuidInJsonDumpStorage(uuid)
    #product = 'bogus'
    #version = '3.xBogus'
    #buildId = '1966060622'
    #nowstamp = time.time()
    #now = dt.datetime.fromtimestamp(nowstamp)
    #processDate = now
    #crashTime = "%d"%(nowstamp - 10000)
    #jsonDoc = {'ProductName':product,'Version':version,'BuildID':buildId,'CrashTime':crashTime}
    #p.insertReportIntoDatabase(cur,uuid,jsonDoc,path,now,[])
    #reportId = 1
    #dbFields = ["signature","processor_notes"]
    #selectSql = 'SELECT %s FROM reports WHERE id=%%s'%(','.join(dbFields))
    #threadNum = 0

    #frameList = [ '%s|%s|module_%x|foo_%X(bar&)|||'%(threadNum,x,x,x) for x in range(15) ]
    #dumper = libutil.CachingIterator(iter(frameList))
    #dumper.secondaryCacheMaximumSize = 2
    #messages = []
    ## check fields before the call
    #cur.execute(selectSql,(reportId,))
    #con.commit()
    #for d in cur.fetchall()[0]:
      #assert None == d, 'Expected None for unanalyzed report, but got %s'%d

    #additionalReportValuesAsDict = p.analyzeFrames(1,dumper,cur,now,threadNum,messages)
    #con.commit()
    #assert not additionalReportValuesAsDict["truncated"], 'Expected not to truncate here, but did. Huh.'
    #assert not messages, 'Expected no error messages, but %s'%(str(messages))
    #i = 0
    #for c in dumper.cache:
      #expected = "%d|%d|module_%x|foo_%X(bar&)|||"%(threadNum,i,i,i)
      #assert expected == c, 'Expected "%s" got "%s"'%(expected, c)
      #i += 1
    ##cur.execute(selectSql,(reportId,))
    ##con.commit()
    ##reportData = cur.fetchall()[0]
    ##sigS = 'foo_%X(bar&)'%0
    ##assert sigS == reportData[0], 'Expected "%s", got %s'%(sigS,reportData[0])
    ##assert '' == reportData[1], 'Expected "None", got %s'%(reportData[1])
    #cur.execute('select * from frames')
    #con.commit()
    #frameData = cur.fetchall()
    #assert 10 == len(frameData)
    #for i in range(len(frameData)):
      #assert (1, now, i, 'foo_%X(bar&)'%(i),) == frameData[i], 'Expected "(1, %s, %d, foo_%X(bar&)", got %s'%(now,i,i,str(frameData[i]))

  #def testAnalyzeFrames_WithBlankLine(self):
    #"""
    #TestProcessorWithExternalBreakpad.testAnalyzeFrames_WithBlankLine(self):
      #check that we get the expected cache, database entries with "unexpected blank line" message
    #"""
    #global me
    #p = eProcessor.ProcessorWithExternalBreakpad(me.config)
    #p.config['crashingThreadFrameThreshold'] = 15
    #con,cur = p.databaseConnectionPool.connectionCursorPair()
    #data = dbtestutil.makeJobDetails({1:1})
    #uuid = data[0][1]
    #createJDS.createTestSet({uuid:createJDS.jsonFileData[uuid]},{'logger':me.logger},p.config.storageRoot)
    #path = p.jsonPathForUuidInJsonDumpStorage(uuid)
    #product = 'bogus'
    #version = '3.xBogus'
    #buildId = '1966060622'
    #nowstamp = time.time()
    #now = dt.datetime.fromtimestamp(nowstamp)
    #processDate = now
    #crashTime = "%d"%(nowstamp - 10000)
    #jsonDoc = {'ProductName':product,'Version':version,'BuildID':buildId,'CrashTime':crashTime}
    #p.insertReportIntoDatabase(cur,uuid,jsonDoc,path,now,[])
    #reportId = 1
    #dbFields = ["signature","processor_notes"]
    #selectSql = 'SELECT %s FROM reports WHERE id=%%s'%(','.join(dbFields))
    #threadNum = 0

    #frameList = [ '%s|%s|module_%x|foo_%X(bar&)|||'%(threadNum,x,x,x) for x in range(5) ]+['']+[ '%s|%s|module_%x|foo_%X(bar&)|||'%(threadNum,x,x,x) for x in range (5,15) ]
    #dumper = libutil.CachingIterator(iter(frameList))
    #dumper.secondaryCacheMaximumSize = 2
    #messages = []
    ## check fields before the call
    #cur.execute(selectSql,(reportId,))
    #con.commit()
    #for d in cur.fetchall()[0]:
      #assert None == d, 'Expected None for unanalyzed report, but got %s'%d
    #d = p.analyzeFrames(1,dumper,cur,now,threadNum,messages)
    #con.commit()
    #assert not d["truncated"], 'Expected not to truncate here, but did. Huh.'
    #assert 1 == len(messages), 'Expected "blank line"  message, but %s'%(str(messages))
    #assert 'An unexpected blank line in this dump was ignored' == messages[0], 'but %s'%messages[0]
    #clist = [ c for c in dumper.cache ]
    #assert clist == frameList, 'but\nclist=%s\nflist=%s'%(str(clist),str(frameList))
    ##cur.execute(selectSql,(reportId,))
    ##reportData = cur.fetchall()[0]
    ##con.commit()
    ##assert 'foo_0(bar&)' == reportData[0], 'Expected "foo_0(bar&)", got %s'%(reportData[0])
    ##assert messages[0] == reportData[1], 'Expected "None", got %s'%(reportData[1])
    #cur.execute('select * from frames')
    #frameData = cur.fetchall()
    #con.commit()
    #assert 10 == len(frameData)
    #for i in range(len(frameData)):
      #assert (1, now, i, 'foo_%X(bar&)'%(i),) == frameData[i], 'Expected "(1, %s, %d, foo_%X(bar&)", got %s'%(now,i,i,str(frameData[i]))

  #def testAnalyzeFrames_Long(self):
    #"""
    #TestProcessorWithExternalBreakpad.testAnalyzeFrames_Long(self):
      #check that we get the expected cache, database entries with secondary cache message for a 'long' set
    #"""
    #global me
    #p = eProcessor.ProcessorWithExternalBreakpad(me.config)
    #p.config['crashingThreadFrameThreshold'] = 5
    #con,cur = p.databaseConnectionPool.connectionCursorPair()
    #data = dbtestutil.makeJobDetails({1:1})
    #uuid = data[0][1]
    #createJDS.createTestSet({uuid:createJDS.jsonFileData[uuid]},{'logger':me.logger},p.config.storageRoot)
    #path = p.jsonPathForUuidInJsonDumpStorage(uuid)
    #product = 'bogus'
    #version = '3.xBogus'
    #buildId = '1966060622'
    #nowstamp = time.time()
    #now = dt.datetime.fromtimestamp(nowstamp)
    #processDate = now
    #crashTime = "%d"%(nowstamp - 10000)
    #jsonDoc = {'ProductName':product,'Version':version,'BuildID':buildId,'CrashTime':crashTime}
    #p.insertReportIntoDatabase(cur,uuid,jsonDoc,path,now,[])
    #reportId = 1
    #dbFields = ["signature","processor_notes"]
    #selectSql = 'SELECT %s FROM reports WHERE id=%%s'%(','.join(dbFields))
    #threadNum = 0

    #frameList = [ '%s|%s|module_%x|foo_%X(bar&)|||'%(threadNum,x,x,x) for x in range(15) ]
    #dumper = libutil.CachingIterator(iter(frameList))
    #dumper.secondaryCacheMaximumSize = 2
    #messages = []
    ## check fields before the call
    #cur.execute(selectSql,(reportId,))
    #con.commit()
    #for d in cur.fetchall()[0]:
      #assert None == d, 'Expected None for unanalyzed report, but got %s'%d
    #d = p.analyzeFrames(1,dumper,cur,now,threadNum,messages)
    #assert d["truncated"], 'Expected it to be truncated with this setup'
    #assert 1 == len(messages), 'Expected one error message, but %s'%(str(messages))
    #assert 'This dump is too long and has triggered the automatic truncation' in messages[0],'But got %s'%(str(messages))
    #i = 0
    #expectedValues = [x for x in range(6)]+[13,14]
    #for c in dumper.cache:
      #expected = "%d|%d|module_%x|foo_%X(bar&)|||"%(threadNum,expectedValues[i],expectedValues[i],expectedValues[i])
      #assert expected == c, 'Expected "%s" got "%s"'%(expected, c)
      #i += 1
    ## commented out because the database isn't updated by analyzeFrames anymore
    ##cur.execute(selectSql,(reportId,))
    ##reportData = cur.fetchall()[0]
    ##con.commit()
    ##assert 'foo_0(bar&)' == reportData[0], 'expected "1", got %s'%(str(reportData[0]))
    ##assert messages[0] == reportData[1], 'Expected %s, but got %s'%(messages[0],reportData[1])

    #cur.execute('select * from frames')
    #frameData = cur.fetchall()
    #con.commit()
    #assert 10 == len(frameData)
    #for i in range(len(frameData)):
      #assert (1, now, i, 'foo_%X(bar&)'%(i),) == frameData[i], 'Expected "(1, %s, %d, foo_%X(bar&)", got %s'%(now,i,i,str(frameData[i]))


  #def testAnalyzeFrames_WithThreadChange(self):
    #"""
    #TestProcessorWithExternalBreakpad.testAnalyzeFrames_WithThreadChange(self):
      #check that we get the expected cache, database entries with "unexpected blank line" message
    #"""
    #global me
    #p = eProcessor.ProcessorWithExternalBreakpad(me.config)
    #p.config['crashingThreadFrameThreshold'] = 15
    #con,cur = p.databaseConnectionPool.connectionCursorPair()
    #data = dbtestutil.makeJobDetails({1:1})
    #uuid = data[0][1]
    #createJDS.createTestSet({uuid:createJDS.jsonFileData[uuid]},{'logger':me.logger},p.config.storageRoot)
    #path = p.jsonPathForUuidInJsonDumpStorage(uuid)
    #product = 'bogus'
    #version = '3.xBogus'
    #buildId = '1966060622'
    #nowstamp = time.time()
    #now = dt.datetime.fromtimestamp(nowstamp)
    #processDate = now
    #crashTime = "%d"%(nowstamp - 10000)
    #jsonDoc = {'ProductName':product,'Version':version,'BuildID':buildId,'CrashTime':crashTime}
    #p.insertReportIntoDatabase(cur,uuid,jsonDoc,path,now,[])
    #reportId = 1
    #dbFields = ["signature","processor_notes"]
    #selectSql = 'SELECT %s FROM reports WHERE id=%%s'%(','.join(dbFields))
    #threadNum = 0

    #frameList = [ '%s|%s|module_%x|foo_%X(bar&)|||'%(threadNum,x,x,x) for x in range(5) ]+[ '%s|%s|module_%x|foo_%X(bar&)|||'%(threadNum+1,5,5,5)]
    #frameList += [ '%s|%s|module_%x|foo_%X(bar&)|||'%(threadNum,x,x,x) for x in range(6,10) ]
    #dumper = libutil.CachingIterator(iter(frameList))
    #dumper.secondaryCacheMaximumSize = 2
    #messages = []
    ## check fields before the call
    #cur.execute(selectSql,(reportId,))
    #for d in cur.fetchall()[0]:
      #assert None == d, 'Expected None for unanalyzed report, but got %s'%d
    #con.commit()
    #d = p.analyzeFrames(1,dumper,cur,now,threadNum,messages)
    #con.commit()
    #assert not d["truncated"]
    #expectedThreadList = [0,0,0,0,0,1]
    #threadList = [int(x[0]) for x in dumper.cache ]
    #assert threadList == expectedThreadList, 'expected %s, but %s'%(str(expectedThreadList),str(threadList))
    ## commented out because the database isn't updated by analyzeFrames anymore
    ##cur.execute(selectSql,(reportId,))
    ##reportData = cur.fetchall()[0]
    ##con.commit()
    ##assert "foo_0(bar&)" == reportData[0], 'but "%s"'%(str(reportData[0]))
    ##assert '' == reportData[1], 'but "%s"'%(str(reportData[1]))
    #cur.execute('select * from frames')
    #frameData = cur.fetchall()
    #con.commit()
    #assert 5 == len(frameData)
    #for i in range(len(frameData)):
      #assert (1, now, i, 'foo_%X(bar&)'%(i),) == frameData[i], 'Expected "(1, %s, %d, foo_%X(bar&)", got %s'%(now,i,i,str(frameData[i]))

  #class CloseableIterator(object):
    #def __init__(self,anIterator):
      #super(TestProcessorWithExternalBreakpad.CloseableIterator,self).__init__()
      #self.theIterator = anIterator
    #def __iter__(self):
      #for x in self.theIterator:
        #yield x
    #def close(self):
      #try:
        #self.theIterator.close()
      #except AttributeError:
        #pass

  #class StubExternalProcessor(eProcessor.ProcessorWithExternalBreakpad):
    #def __init__(self, config):
      #super(TestProcessorWithExternalBreakpad.StubExternalProcessor, self).__init__(config)
      #me.logger.info("Constructed StubExternalProcessor: extends ProcessorWithExternalBreakpad")
      #self.data = []
      #self.returncode = 0
    #def wait(self): # no need for another stub when we have this one handy
      #me.logger.info("wait() was called. Returning %s",self.returncode)
      #return self.returncode
    #def invokeBreakpadStackdump(self, dumpfilePathname):
      #me.logger.info("%s - IGNORING %s", 'ProbablyMainThread', dumpfilePathname)
      #self.iterator = libutil.CachingIterator(TestProcessorWithExternalBreakpad.CloseableIterator(iter(self.data)))
      #try:
        #self.iterator.secondaryCacheMaximumSize = self.secondaryCacheMaximumSize
      #except AttributeError:
        #pass
      #return (self.iterator,self)

  #def testDoBreakpadStackDumpAnalysis_Empty(self):
    #"""
    #TestProcessorWithExternalBreakpad.testDoBreakpadStackDumpAnalysis_Empty(self):
      #check that we raise ErrorInBreakpadStackwalkException if returncode is neither None nor 0
      #check that we succeed, with error messages, if the return code is None or if it is 0
    #"""
    #global me
    #p = TestProcessorWithExternalBreakpad.StubExternalProcessor(me.config)
    #con,cur = p.databaseConnectionPool.connectionCursorPair()
    #try:
      #data = dbtestutil.makeJobDetails({1:3})
      #uuid0 = data[0][1]
      #uuid1 = data[1][1]
      #uuid2 = data[2][1]
      #createJDS.createTestSet({uuid0:createJDS.jsonFileData[uuid0],uuid1:createJDS.jsonFileData[uuid1],uuid2:createJDS.jsonFileData[uuid2]},{'logger':me.logger},p.config.storageRoot)
      #jpath0 = p.jsonPathForUuidInJsonDumpStorage(uuid0)
      #dpath0 = p.dumpPathForUuidInJsonDumpStorage(uuid0)
      #jpath1 = p.jsonPathForUuidInJsonDumpStorage(uuid1)
      #dpath1 = p.dumpPathForUuidInJsonDumpStorage(uuid1)
      #jpath2 = p.jsonPathForUuidInJsonDumpStorage(uuid2)
      #dpath2 = p.dumpPathForUuidInJsonDumpStorage(uuid2)
      #product = 'bogus'
      #version = '3.xBogus'
      #buildId = '1966060622'
      #nowstamp = time.time()
      #now = dt.datetime.fromtimestamp(nowstamp)
      #processDate = now
      #crashTime = "%d"%(nowstamp - 10000)
      #jsonDoc = {'ProductName':product,'Version':version,'BuildID':buildId,'CrashTime':crashTime}
      #uuid0ReportRecordAsDict = p.insertReportIntoDatabase(cur,uuid0,jsonDoc,jpath0,now,[])
      #uuid1ReportRecordAsDict = p.insertReportIntoDatabase(cur,uuid1,jsonDoc,jpath1,now,[])
      #uuid2ReportRecordAsDict = p.insertReportIntoDatabase(cur,uuid2,jsonDoc,jpath2,now,[])
      #reportId = 1
      #messages = []

      #p.returncode = 2
      #try:
        #additionalReportValuesAsDict = p.doBreakpadStackDumpAnalysis(reportId,uuid0,dpath0,cur,now,messages)
      #except processor.ErrorInBreakpadStackwalkException, x:
        #assert 4 == len(messages), 'Expected no header, no thread, no signature, no frame. But %s'%(str(messages))
      #except Exception, x:
        #assert False, "Unexpected exception: %s %s" % (type(x), x)

      #p.returncode = 0
      #reportId += 1
      #messages = []
      #additionalReportValuesAsDict = p.doBreakpadStackDumpAnalysis(reportId,uuid1,dpath1,cur,now,messages)
      #assert 4 == len(messages), 'Expected no header, no thread, no signature, no frame. But %s'%(str(messages))
      #assert additionalReportValuesAsDict["dump"] =='', "Expected an empty dump, but got: %s" % additionalReportValuesAsDict["dump"]

      #p.returncode = None
      #reportId += 1
      #messages = []
      #additionalReportValuesAsDict = p.doBreakpadStackDumpAnalysis(reportId,uuid2,dpath2,cur,now,messages)
      #assert 4 == len(messages), 'Expected no header, no thread, no signature, no frame. But %s'%(str(messages))
      #assert additionalReportValuesAsDict["dump"] =='', "Expected an empty dump, but got: %s" % additionalReportValuesAsDict["dump"]
    #finally:
      #con.rollback()

  #def testDoBreakpadStackDumpAnalysis_Full(self):
    #"""
    #TestProcessorWithExternalBreakpad.testDoBreakpadStackDumpAnalysis_Full(self):
      #check that we succeed and add data to the dumps table
    #"""
    #global me
    #p = TestProcessorWithExternalBreakpad.StubExternalProcessor(me.config)
    #p.config['crashingThreadTailFrameThreshold'] = 3
    #p.config['crashingThreadFrameThreshold'] = 8
    #p.secondaryCacheMaximumSize = 2
    #threadNum = 0
    #headerList = ['CPU|cpuName|cpuVersion','OS|osName|osVersion','Crash|gerbils|0xdeadbeef|0','']
    #frameList =  [ '%s|%s|module_%x|foo_%X(bar&)|||'%(threadNum,x,x,x) for x in range(15) ]
    #p.data = headerList + frameList
    #con,cur = p.databaseConnectionPool.connectionCursorPair()
    #data = dbtestutil.makeJobDetails({1:3})
    #uuid0 = data[0][1]
    #uuid1 = data[1][1]
    #uuid2 = data[2][1]
    #createJDS.createTestSet({uuid0:createJDS.jsonFileData[uuid0],
                             #uuid1:createJDS.jsonFileData[uuid1],
                             #uuid2:createJDS.jsonFileData[uuid2]},
                            #{'logger':me.logger},p.config.storageRoot)
    #jpath0 = p.jsonPathForUuidInJsonDumpStorage(uuid0)
    #dpath0 = p.dumpPathForUuidInJsonDumpStorage(uuid0)
    #jpath1 = p.jsonPathForUuidInJsonDumpStorage(uuid1)
    #dpath1 = p.dumpPathForUuidInJsonDumpStorage(uuid1)
    #jpath2 = p.jsonPathForUuidInJsonDumpStorage(uuid2)
    #dpath2 = p.dumpPathForUuidInJsonDumpStorage(uuid2)
    #product = 'bogus'
    #version = '3.xBogus'
    #buildId = '1966060622'
    #nowstamp = time.time()
    #now = dt.datetime.fromtimestamp(nowstamp)
    #processDate = now
    #crashTime = "%d"%(nowstamp - 10000)
    #jsonDoc = {'ProductName':product,'Version':version,'BuildID':buildId,'CrashTime':crashTime}
    #p.insertReportIntoDatabase(cur,uuid0,jsonDoc,jpath0,now,[])
    #p.insertReportIntoDatabase(cur,uuid1,jsonDoc,jpath1,now,[])
    #p.insertReportIntoDatabase(cur,uuid2,jsonDoc,jpath2,now,[])
    #reportId = 1
    #messages = []
    #p.doBreakpadStackDumpAnalysis(reportId,uuid0,dpath0,cur,now,messages)
    #con.commit()
    #assert 1 == len(messages)
    #assert 'has triggered the automatic truncation routine' in messages[0],'But %s'%(messages[0])

    ##cur.execute('select * from dumps where report_id = %s',(reportId,))
    ##ddata = cur.fetchall()[0]
    ##con.commit()
    ##assert len(p.data) > len(p.iterator.cache), "Expected to lose some to the tailframe truncation, but %s ?>? %s"%(len(p.data),len(p.iterator.cache))
    ##assert ''.join(p.iterator.cache) == ddata[-1]

  #def testGetVersionIfFlashModule_noKnownFlashDebugIdentifiers(self):
    #"""
    #testProcessorWithExternalBreakpad:TestProcessorWithExternalBreakpad.testGetVersionIfFlashModule_noKnownFlashDebugIdentifiers(self):
    #"""
    ## the final item of the data part is an index number into the list of cases, used for debugging a failure
    #cases = [
      ##[[module,filename,version,debugfilename,debugid,junk,junk,index],expected] # where debugid = SOMETHING-index
      #[['Module','Athabasca','toot','NPSWF32.dll','DBGID','0x00','0x01','0'],None],
      #[['Module','NPSWF32.dll','','NPSWF32.dll','DBGID','0x00','0x01','1'],None],
      #[['Module','NPSWF32.dll','toot','NPSWF32.dll','DBGID','0x00','0x01','2'],'toot'],
      #[['Module','NPSWF32.exe','toot','NPSWF32.exe','DBGID','0x00','0x01','3'],None],
      #[['Module','NPSWF32alpha.dll','toot','NPSWF32alpha.dll','DBGID','0x00','0x01','4'],None],
      #[['Module','npswf32.dll','toot','npswf32.dll','DBGID','0x00','0x01','5'],None],
      #[['Module','libflashplayer.so','','libflashplayer.so','DBGID','0x00','0x01','6'],None],
      #[['Module','libflashplayer.a','','libflashpayer.a','DBGID','0x00','0x01','7'],None],
      #[['Module','libflashplayer.so','toot','libflashplayer.so','DBGID','0x00','0x01','8'],'toot'],
      #[['Module','libflashplayer.a','toot','libflashplayer.a','DBGID','0x00','0x01','9'],'toot'],
      #[['Module','libflashplayer-3.2.1.so','toot','libflashplayer-3.2.1.so','DBGID','0x00','0x01','10'],'toot'],
      #[['Module','libflashplayer-3.2.1.a','toot','libflashplayer-3.2.1.a','DBGID','0x00','0x01','11'],'toot'],
      #[['Module','libflashplayer-3.2.1.so','','libflashplayer-3.2.1.so','DBGID','0x00','0x01','12'],'-3.2.1'],
      #[['Module','libflashplayer-3.2.1.a','','libflashplayer-3.2.1.a','DBGID','0x00','0x01','13'],'-3.2.1'],
      #[['Module','Flash Player','','Flash Player','DBGID','0x00','0x01','14'],''],
      #[['Module','Flash Player','toot','Flash Player','DBGID','0x00','0x01','15'],'toot'],
      #[['Module','FlashPlayer','','FlashPlayer','DBGID','0x00','0x01','16'],''],
      #[['Module','FlashPlayer','toot','FlashPlayer','DBGID','0x00','0x01','17'],'toot'],
      #[['Module','FlashPlayer-10.3','','FlashPlayer-10.3','DBGID','0x00','0x01','18'],'10.3'],
      #[['Module','FlashPlayer-10.3','toot','FlashPlayer-10.3','DBGID','0x00','0x01','19'],'toot'],
      #[['Module','Flash Player-10.3','','Flash Player-10.3','DBGID','0x00','0x01','20'],'10.3'],
      #[['Module','Flash Player-10.3','toot','Flash Player-10.3','DBGID','0x00','0x01','21'],'toot'],
      #]
    #global me
    #p = TestProcessorWithExternalBreakpad.StubExternalProcessor(me.config)

    #for data,expected in cases:
      #got = p.getVersionIfFlashModule(data)
      #assert expected == got, 'At %s: Given "%s", expected "%s" but got "%s"'%(data[-1],data[1],expected,got)

  #def testGetVersionIfFlashModule_withKnownFlashDebugIdentifiers(self):
    #"""
    #testProcessorWithExternalBreakpad:TestProcessorWithExternalBreakpad.testGetVersionIfFlashModule_withKnownFlashDebugIdentifiers
    #"""
    #cases = [
      #[['Module','Athabasca','toot','NPSWF32.dll','DBGID-0','0x00','0x01','0'],None],
      #[['Module','NPSWF32.dll','','NPSWF32.dll','DBGID-1','0x00','0x01','1'],'moo'],
      #[['Module','NPSWF32.dll','toot','NPSWF32.dll','DBGID-2','0x00','0x01','2'],'toot'],
      #[['Module','NPSWF32.exe','toot','NPSWF32.exe','DBGID-3','0x00','0x01','3'],None],
      #[['Module','NPSWF32alpha.dll','toot','NPSWF32alpha.dll','DBGID-4','0x00','0x01','4'],None],
      #[['Module','npswf32.dll','toot','npswf32.dll','DBGID-5','0x00','0x01','5'],None],
      #[['Module','libflashplayer.so','','libflashplayer.so','DBGID-6','0x00','0x01','6'],'moo'],
      #[['Module','libflashplayer.a','','libflashpayer.a','DBGID-7','0x00','0x01','7'],'moo'],
      #[['Module','libflashplayer.so','toot','libflashplayer.so','DBGID-8','0x00','0x01','8'],'toot'],
      #[['Module','libflashplayer.a','toot','libflashplayer.a','DBGID-9','0x00','0x01','9'],'toot'],
      #[['Module','libflashplayer-3.2.1.so','toot','libflashplayer-3.2.1.so','DBGID-10','0x00','0x01','10'],'toot'],
      #[['Module','libflashplayer-3.2.1.a','toot','libflashplayer-3.2.1.a','DBGID-11','0x00','0x01','11'],'toot'],
      #[['Module','libflashplayer-3.2.1.so','','libflashplayer-3.2.1.so','DBGID-12','0x00','0x01','12'],'-3.2.1'],
      #[['Module','libflashplayer-3.2.1.a','','libflashplayer-3.2.1.a','DBGID-13','0x00','0x01','13'],'-3.2.1'],
      #[['Module','Flash Player','','Flash Player','DBGID-14','0x00','0x01','14'],'moo'],
      #[['Module','Flash Player','toot','Flash Player','DBGID-15','0x00','0x01','15'],'toot'],
      #[['Module','FlashPlayer','','FlashPlayer','DBGID-16','0x00','0x01','16'],'moo'],
      #[['Module','FlashPlayer','toot','FlashPlayer','DBGID-17','0x00','0x01','17'],'toot'],
      #[['Module','FlashPlayer-10.3','','FlashPlayer-10.3','DBGID-18','0x00','0x01','18'],'10.3'],
      #[['Module','FlashPlayer-10.3','toot','FlashPlayer-10.3','DBGID-19','0x00','0x01','19'],'toot'],
      #[['Module','Flash Player-10.3','','Flash Player-10.3','DBGID-20','0x00','0x01','20'],'10.3'],
      #[['Module','Flash Player-10.3','toot','Flash Player-10.3','DBGID-21','0x00','0x01','21'],'toot'],
      #]
    #global me
    #config = copy.copy(me.config)
    #config['knownFlashDebugIdentifiers'] = {
      #'DBGID-0':'moo',
      #'DBGID-1':'moo',
      #'DBGID-2':'moo',
      #'DBGID-3':'moo',
      #'DBGID-4':'moo',
      #'DBGID-5':'moo',
      #'DBGID-6':'moo',
      #'DBGID-7':'moo',
      #'DBGID-8':'moo',
      #'DBGID-9':'moo',
      #'DBGID-10':'moo',
      #'DBGID-11':'moo',
      #'DBGID-12':'moo',
      #'DBGID-13':'moo',
      #'DBGID-14':'moo',
      #'DBGID-15':'moo',
      #'DBGID-16':'moo',
      #'DBGID-17':'moo',
      #'DBGID-18':'moo',
      #'DBGID-19':'moo',
      #'DBGID-20':'moo',
      #'DBGID-21':'moo',
      #}

    #p = TestProcessorWithExternalBreakpad.StubExternalProcessor(config)

    #for data,expected in cases:
      #got = p.getVersionIfFlashModule(data)
      #assert expected == got, 'At %s: Given "%s", expected "%s" but got "%s"'%(data[-1],data[1],expected,got)

