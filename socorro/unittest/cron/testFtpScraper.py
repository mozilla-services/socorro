# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import errno
import logging
import os

import psycopg2

import unittest
import socorro.lib.buildutil as buildutil
import socorro.lib.ConfigurationManager as cfgManager
import socorro.lib.util
import socorro.lib.psycopghelper as psy
import socorro.cron.ftpscraper as ftpscraper
from socorro.unittest.testlib.loggerForTest import TestingLogger
from socorro.unittest.testlib.testDB import TestDB
import socorro.unittest.testlib.expectations as exp
import cronTestconfig as testConfig


class Me:
    """
    Initialize once per module
    """
    pass
me = None


def setup_module():
    global me
    if me:
        return
    me = Me()
    me.config = cfgManager.newConfiguration(configurationModule=testConfig,
          applicationName='Testing ftpscraper')
    myDir = os.path.split(__file__)[0]
    if not myDir:
        myDir = '.'
    replDict = {'testDir': '%s' % myDir}
    for i in me.config:
        try:
            me.config[i] = me.config.get(i) % (replDict)
        except:
            pass
    me.logFilePathname = me.config.logFilePathname
    if not me.logFilePathname:
        me.logFilePathname = 'logs/ftpscraper_test.log'
    logFileDir = os.path.split(me.logFilePathname)[0]
    try:
        os.makedirs(logFileDir)
    except OSError, x:
        if errno.EEXIST == x.errno:
            pass
        else:
            raise
    fileLog = logging.FileHandler(me.logFilePathname, 'a')
    fileLog.setLevel(logging.DEBUG)
    fileLogFormatter = logging.Formatter(
          '%(asctime)s %(levelname)s - %(message)s')
    fileLog.setFormatter(fileLogFormatter)
    me.fileLogger = logging.getLogger("ftpscraper")
    me.fileLogger.addHandler(fileLog)
    # Got trouble?    See what's happening by uncommenting the next three lines
    #stderrLog = logging.StreamHandler()
    #stderrLog.setLevel(10)
    #me.fileLogger.addHandler(stderrLog)

    me.dsn = "host=%s dbname=%s user=%s password=%s" % \
          (me.config.databaseHost, me.config.databaseName,
           me.config.databaseUserName, me.config.databasePassword)
    me.testDB = TestDB()
    me.testDB.removeDB(me.config, me.fileLogger)
    me.testDB.createDB(me.config, me.fileLogger)
    try:
        me.conn = psycopg2.connect(me.dsn)
        me.cur = me.conn.cursor(cursor_factory=psy.LoggingCursor)
    except Exception, x:
        print "Exception in setup_module() connecting to db: ", type(x), x
        socorro.lib.util.reportExceptionAndAbort(me.fileLogger)


def teardown_module():
    global me
    me.testDB.removeDB(me.config, me.fileLogger)
    me.conn.close()
    try:
        os.unlink(me.logFilePathname)
    except:
        pass


class TestFtpScraper(unittest.TestCase):
    def setUp(self):
        global me
        self.config = cfgManager.newConfiguration(
              configurationModule=testConfig,
              applicationName='Testing ftpscraper')

        myDir = os.path.split(__file__)[0]
        if not myDir:
            myDir = '.'
        replDict = {'testDir': '%s' % myDir}
        for i in self.config:
            try:
                self.config[i] = self.config.get(i) % (replDict)
            except:
                pass
        self.logger = TestingLogger(me.fileLogger)

        self.testConfig = cfgManager.Config([('t', 'testPath',
                                              True, './TEST-BUILDS', ''),
                                             ('f', 'testFileName',
                                              True, 'lastrun.pickle', '')])
        self.testConfig["persistentDataPathname"] = os.path.join(
              self.testConfig.testPath, self.testConfig.testFileName)

    def tearDown(self):
        self.logger.clear()

    def test_getLinks(self):
        self.config.products = ('PRODUCT1', 'PRODUCT2')
        self.config.base_url = 'http://www.example.com/'

        fake_response_url = "%s%s" % (self.config.base_url,
              self.config.products[0])
        fake_response_contents = """
             blahblahblahblahblah
             <a href="product1-v1.en-US.p1.txt">product1-v1.en-US.p1.txt</a>
             <a href="product1-v1.en-US.p1.zip">product1-v1.en-US.p1.zip</a>
             <a href="product2-v2.en-US.p2.txt">product2-v2.en-US.p2.txt</a>
             <a href="product2-v2.en-US.p2.zip">product2-v2.en-US.p2.zip</a>
             blahblahblahblahblah
        """

        fakeResponse = exp.DummyObjectWithExpectations()
        fakeResponse.code = 200
        fakeResponse.expect('read', (), {}, fake_response_contents)
        fakeResponse.expect('close', (), {})

        fakeUrllib2 = exp.DummyObjectWithExpectations()
        fakeUrllib2.expect('urlopen', (fake_response_url,), {}, fakeResponse)

        actual = ftpscraper.getLinks('http://www.example.com/PRODUCT1',
            startswith='product1', urllib=fakeUrllib2)
        expected = ['product1-v1.en-US.p1.txt',
                    'product1-v1.en-US.p1.zip']
        assert actual == expected, "expected %s, got %s" % (expected, actual)

        fakeResponse = exp.DummyObjectWithExpectations()
        fakeResponse.code = 200
        fakeResponse.expect('read', (), {}, fake_response_contents)
        fakeResponse.expect('close', (), {})

        fakeUrllib2 = exp.DummyObjectWithExpectations()
        fakeUrllib2.expect('urlopen', (fake_response_url,), {}, fakeResponse)

        expected = ['product1-v1.en-US.p1.zip',
                    'product2-v2.en-US.p2.zip']
        actual = ftpscraper.getLinks('http://www.example.com/PRODUCT1',
              endswith='.zip', urllib=fakeUrllib2)
        assert actual == expected, "expected %s, got %s" % (expected, actual)

    def test_parseInfoFile(self):
        self.config.products = ('PRODUCT1', 'PRODUCT2')
        self.config.base_url = 'http://www.example.com/'

        fake_response_url = "%s%s" % (self.config.base_url,
              self.config.products[0])
        fake_response_contents = """
            20111011042016
            http://hg.mozilla.org/releases/mozilla-aurora/rev/327f5fdae663
        """

        fakeResponse = exp.DummyObjectWithExpectations()
        fakeResponse.code = 200
        fakeResponse.expect('read', (), {}, fake_response_contents)
        fakeResponse.expect('close', (), {})

        fakeUrllib2 = exp.DummyObjectWithExpectations()
        fakeUrllib2.expect('urlopen', (fake_response_url,), {}, fakeResponse)

        rev = 'http://hg.mozilla.org/releases/mozilla-aurora/rev/327f5fdae663'
        expected = {
          'buildID': '20111011042016',
          'rev': rev
        }
        actual = ftpscraper.parseInfoFile('http://www.example.com/PRODUCT1',
              nightly=True, urllib=fakeUrllib2)
        assert actual == expected, "expected %s, got %s" % (expected, actual)

        fake_response_contents = """
            buildID=20110705195857
        """

        fakeResponse = exp.DummyObjectWithExpectations()
        fakeResponse.code = 200
        fakeResponse.expect('read', (), {}, fake_response_contents)
        fakeResponse.expect('close', (), {})

        fakeUrllib2 = exp.DummyObjectWithExpectations()
        fakeUrllib2.expect('urlopen', (fake_response_url,), {}, fakeResponse)
        expected = {'buildID': '20110705195857'}
        actual = ftpscraper.parseInfoFile('http://www.example.com/PRODUCT1',
              nightly=False, urllib=fakeUrllib2)
        assert actual == expected, "expected %s, got %s" % (expected, actual)
