# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import sys
import os
import copy
import cStringIO
import datetime

### DynamicConfig and its module should be a drop-in replacement for Config and its module
### The line below works, but it seemed overkill to duplicate the whole test so
### Just left this here as a reminder to play with it from time to time.
#import socorro.lib.ConfigurationManager as CM
import socorro.lib.dynamicConfigurationManager as CM

import optionfile

class HelpHandler:
  def __init__(self):
    self.data = ''
  def handleHelp(self, config):
    self.stringIO = cStringIO.StringIO()
    config.outputCommandSummary(self.stringIO,False)
    self.data = self.stringIO.getvalue()
    self.stringIO.close()

class TestConfigurationManager(unittest.TestCase):
  def __findConfigTstPath(self):
    if os.path.exists(os.path.join('.','config.tst')):
      return os.path.join('.','config.tst')
    # else
    dir = os.path.split(__file__)[0]
    return os.path.join(dir,'config.tst')
#     for dirpath,dirnames,filenames in os.walk("."):
#       if 'config.tst' in filenames:
#         return os.path.join(dirpath,'config.tst');
#     return os.path.join('.','config.tst') # this will give a nice failure message

  def setUp(self):
    self.keepargv = copy.copy(sys.argv)
    self.keepenviron = os.environ.copy()
    self.configTstPath = self.__findConfigTstPath()
    assert os.path.exists(self.configTstPath), "Why is this not in existence: %s"%(self.configTstPath)
    # all our tests depend on setting their own sys.argv AFTER the test has begun to run
    # In order to avoid trouble, blow away all the params that nosetests should 'use up'
    if 'nosetests' in sys.argv[0]:
      sys.argv = sys.argv[:1] # yes: Throw away all the params but the executable name

  def tearDown(self):
    sys.argv = copy.copy(self.keepargv)
    os.environ = self.keepenviron.copy()

  def testNewConfiguration(self):
    '''
    TestConfigurationManager.testNewConfiguration(self)
    Trick: To call f(**kwargs) with a dictionary d as the single arg, chant f(**d)
    '''
    opts = []
    args = {}
    args['automaticHelp'] = False

    # Test for empty
    conf = CM.newConfiguration(**args)
    assert(not conf.internal.allowableOptionDictionary)

    # Test for autoHelp
    args['automaticHelp'] = True
    conf = CM.newConfiguration(**args)
    assert(2 == len(conf.internal.allowableOptionDictionary))

    # Test for another legal option
    opts.append(('c','chickensoup',False,False,'Help for the ailing'))
    args['automaticHelp'] = True
    args['configurationOptionsList'] = opts
    conf = CM.newConfiguration(**args)
    assert(4 == len(conf.internal.allowableOptionDictionary))

    # Test a config module
    conf = CM.newConfiguration(automaticHelp=False,configurationModule=optionfile)
    cd = conf.internal.allowableOptionDictionary
    assert(5 == len(cd)),'but cd is %s'%cd
    assert ['T', 'testSingleCharacter', True, None] == cd.get('T')[:-1],'but got %s' % (str(cd.get('T')[:-1]))
    assert 'testSingleCharacter imported from' in cd.get('T')[-1],'but got %s' % (str(cd.get('T')[-1]))
    assert 'optionfile' in cd.get('T')[-1],'but got %s' % (str(cd.get('T')[-1]))
    #assert ['T', 'testSingleCharacter', True, None, 'testSingleCharacter imported from optionfile'] == cd.get('T'),'but got %s' % (str(cd.get('T')))
    assert [None, 'testDefault', True, 'default'] == cd.get('testDefault')[:-1], "but got %s" %(str(cd.get('testDefault')[:-1]))
    assert 'testDefault imported from' in cd.get('testDefault')[-1], "but got %s" %(cd.get('testDefault')[-1])
    assert 'optionfile' in cd.get('testDefault')[-1],  "but got %s" %(cd.get('testDefault')[-1])
    #assert([None, 'testDefault', True, 'default', 'testDefault imported from optionfile'] == cd.get('testDefault'))
    assert([None, 'testDoc', True, None, 'test doc'] == cd.get('testDoc'))
    assert [None, 'testNil', True, None] == cd.get('testNil')[:-1], "but got %s" %(str(cd.get('testNil')[:-1]))
    assert 'testNil imported from' in cd.get('testNil')[-1], "but got %s" %(cd.get('testNil')[-1])
    assert 'optionfile' in cd.get('testNil')[-1], "but got %s" %(cd.get('testNil')[-1])
    #assert([None, 'testNil', True, None, 'testNil imported from optionfile'] == cd.get('testNil'))

    # Test failure with good option, bad file
    try:
      copt = [('c',  'config', True, './badone', "the badconfig file")]
      CM.newConfiguration(configurationOptionsList=copt,optionNameForConfigFile = 'config', configurationFileRequired = True)
      assert(False)
    except CM.ConfigFileMissingError, e:
      assert(True)
    except Exception, e:
      assert(False)
    # Test failure with bad option, good file
    try:
      copt = [('c',  'cdvfrbgt', True, './config.tst', "the test config file")]
      CM.newConfiguration(automaticHelp=False,configurationOptionsList=copt,optionNameForConfigFile = 'config', configurationFileRequired = True)
      assert(False)
    except CM.ConfigFileOptionNameMissingError, e:
      assert(True)
    except Exception, e:
      assert(False)

  def testAcceptAutoCommandLineHelp(self):
    opts = []
    args = {}
    args['automaticHelp'] = True
    args['configurationOptionsList'] = opts
    hh = HelpHandler()
    args['helpHandler'] = hh.handleHelp
    sys.argv.append('--help')
    conf = CM.newConfiguration(**args)
    assert("--help" in hh.data)
    assert("print this list" in hh.data)

  def testAcceptUserCommandLineHelp(self):
    opts = [('h','help',False,False,'another help')]
    args = {}
    args['automaticHelp'] = False
    args['configurationOptionsList'] = opts
    hh = HelpHandler()
    args['helpHandler'] = hh.handleHelp
    sys.argv.append('--help')
    conf = CM.newConfiguration(**args)
    assert("--help" in hh.data)
    assert("another help" in hh.data)

  def testAcceptCommandLine(self):
    opts = []
    args = {}
    opts.append(('c','chickensoup',False,False,'help for the ailing'))
    opts.append(('r','rabbit', True, '', 'rabbits are bunnies'))
    args['configurationOptionsList'] = opts
    sys.argv.append('-c')
    sys.argv.append('--rabbit=bunny')
    conf = CM.newConfiguration(**args)
    assert('chickensoup' in conf)
    assert('rabbit' in conf)
    assert('bunny' == conf.rabbit)

  def testAcceptEnvironment(self):
    opts = []
    args = {}
    opts.append(('c','chickensoup',False,False,'help for the ailing'))
    opts.append(('r','rabbit', True, '', 'rabbits are bunnies'))
    args['configurationOptionsList'] = opts
    os.environ['chickensoup']=''
    os.environ['r'] = 'bunny-rabbit'
    conf = CM.newConfiguration(**args)
    assert('chickensoup' in conf)
    assert('rabbit' in conf)
    assert('bunny-rabbit' == conf.rabbit)

  def testAcceptConfigFile(self):
    # Test failure with good config file, unknown option in that file
    try:
      copt = [('c',  'config', True, self.configTstPath, "the test config file")]
      CM.newConfiguration(configurationOptionsList=copt,optionNameForConfigFile = 'config', configurationFileRequired = True)
      assert(False)
    except CM.NotAnOptionError, e:
      assert(True)
    except Exception, e:
      assert(False), "Unexpected exception (%s): %s"% (type(e),e)

    copt = [('c',  'config', True, self.configTstPath, "the test config file"),('r','rabbit', True, 'bambi', 'rabbits are bunnies')]
    copt.append(('b','badger',True,'gentle','some badgers are gentle'))
    conf = CM.newConfiguration(automaticHelp=False,configurationOptionsList=copt,optionNameForConfigFile = 'config', configurationFileRequired = True)
    assert('bunny' == conf.rabbit)
    assert('this badger=awful' == conf.badger)
    assert(3 == len(conf.keys())) # None of the comment or blank lines got eaten

  def testAcceptTypePriority(self):
    '''testConfigurationManager:TestConfigurationManager.testAcceptTypePriority
    Assure that commandline beats config file beats environment beats defaults'''
    copt = [('c',  'config', True, self.configTstPath, "the test config file"),('r','rabbit', True, 'bambi', 'rabbits are bunnies')]
    copt.append(('b','badger',True,'gentle','some badgers are gentle'))
    copt.append(('z','zeta', True, 'zebra', 'zebras ooze'))
    os.environ['badger'] = 'bloody'
    os.environ['zeta'] = 'zymurgy'
    sys.argv.append('--rabbit=kangaroo')
    conf = CM.newConfiguration(automaticHelp=False,configurationOptionsList=copt,optionNameForConfigFile = 'config', configurationFileRequired = True)
    assert('kangaroo' == conf.rabbit) # command line beats config file
    assert('this badger=awful' == conf.badger) # config file beats environment
    assert('zymurgy' == conf.zeta)

  def testTimeDeltaConverter(self):
    testCases = [
      ('1',datetime.timedelta(seconds=1)),
      ('1:2',datetime.timedelta(minutes=1,seconds=2)),
      ('1:2:3',datetime.timedelta(hours=1,minutes=2,seconds=3)),
      ('1:2:3:4',datetime.timedelta(days=1,hours=2,minutes=3,seconds=4)),
      (datetime.timedelta(days=12,microseconds=11),datetime.timedelta(days=12,microseconds=11)),
      (39,39),
      ]
    for t in testCases:
      val = CM.timeDeltaConverter(t[0])
      assert t[1] == val,'From %s, got %s (not %s)'%(str(t),str(val),str(t[1]))

if __name__ == "__main__":
  unittest.main()
