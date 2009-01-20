import unittest
import sys
import os
import copy
import cStringIO
import socorro.lib.ConfigurationManager as CM
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
    for dirpath,dirnames,filenames in os.walk("."):
      if 'config.tst' in filenames:
        return os.path.join(dirpath,'config.tst');
    return os.path.join('.','config.tst') # this will give a nice failure message

  def setUp(self):
    self.keepargv = copy.copy(sys.argv)
    self.keepenviron = os.environ.copy()
    self.configTstPath = self.__findConfigTstPath()
    
  def tearDown(self):
    sys.argv = copy.copy(self.keepargv)
    os.environ = self.keepenviron.copy()

  def testNewConfiguration(self):
    '''
    Trick: To call f(**kwargs) with a dictionary d as the single arg, chant f(**d)
    '''
    opts = []
    args = {}
    args['automaticHelp'] = False

    # Test for empty
    conf = CM.newConfiguration(**args)
    assert(not conf.allowableOptionDictionary)

    # Test for autoHelp
    args['automaticHelp'] = True
    conf = CM.newConfiguration(**args)
    assert(2 == len(conf.allowableOptionDictionary))

    # Test for another legal option
    opts.append(('c','chickensoup',False,False,'Help for the ailing'))
    args['automaticHelp'] = True
    args['configurationOptionsList'] = opts
    conf = CM.newConfiguration(**args)
    assert(4 == len(conf.allowableOptionDictionary))

    # Test a config module
    conf = CM.newConfiguration(automaticHelp=False,configurationModule=optionfile)
    cd = conf.allowableOptionDictionary
    assert(5 == len(cd))
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
    '''Assure that commandline beats config file beats environment beats defaults'''
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

if __name__ == "__main__":
  unittest.main()
