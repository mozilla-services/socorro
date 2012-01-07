import datetime
import signal

import socorro.lib.ConfigurationManager as socorro_config
from socorro.lib.ConfigurationManager import ConfigFileMissingError, ConfigFileOptionNameMissingError, NotAnOptionError, OptionError, CannotConvert, Option
from socorro.lib.ConfigurationManager import ioConverter, dateTimeConverter, timeDeltaConverter, booleanConverter
from socorro.lib.datetimeutil import utc_now


def newConfiguration(**kwargs):
  """ This used as an alternate constructor for class Config so that applications can
      be lax in defining all the required paramters in the right order.
  """
  kw = socorro_config.getDefaultedConfigOptions()
  kw.update(kwargs)
  return DynamicConfig(**kw)

def noop(*args):
  pass

def createDefaultExecUpdater(configPath):
  """
  Factory for default updateFunction for DynamicConfig that reads a config file
  Usage: execUpdater = createDefaultExecUpdter(local_path_to_config_file_py,myconfig)
         dynamicConfigInstance.updateFunction = execUpdater
         ...
         dynamicConfigInstance.update()
  """
  def defaultExecUpdater(config):
    globs = {}
    locs = {}
    execfile(configPath,globs,locs)
    for k,v in  locs.items():
      if socorro_config.Option == type(v):
        config[k] = v.__dict__['default']

  return defaultExecUpdater

def createDefaultDbUpdater(cursor,tableName,configKey='configKey',configValue='configValue',configConversion=None):
  """
  Factory for default updateFunction for DynamicConfig that reads a database table:
    Two columns are required:
      column containing the config key, column containing the config value
    One column is optional: contains the name of the conversionFunction that takes text to type:
      - if not supplied, all values are treated as text. Otherwise, the following steps are tried in order
      - if the conversion is an un-scoped function in the ConfigurationManager module, it is called
      - an attempt is made to eval a function of the given name, to get builtins (see "Injection" below)
      - upon failure, the value reverts to text
    Injection: You may inject your own converter into the dynamicConfigurationManager module so it can be found:
      import socorro.lib.dynamicConfigurationModule as dcm; ...; dcm.myFunction = myFunction
  Usage: execUpdater = createDefaultDbUpdater(cursor,tableName[,configKey=columnName] [,configValue=columnName])
         dynamicConfigInstance.updateFunction = execUpdater
         ...
         dynamicConfigInstance.update()
  """
  def defaultDbUpdater(config):
    sql = 'SELECT %s, %s, NULL from %s'%(configKey,configValue,tableName)
    if configConversion:
      sql = 'SELECT %s, %s, %s from %s'%(configKey,configValue,configConversion,tableName)
    try:
      cursor.execute(sql)
      values = cursor.fetchall()
      for (k,v,c) in values:
        if c:
          v = tryConvert(v,c)
        config[k] = v
    finally:
      cursor.connection.rollback() # no update, so rollback sufficient
  return defaultDbUpdater

def tryConvert(value,converter):
  try:
    f = getattr(socorro_config,converter)
    return f(value)
  except Exception,x: # socorro_config doesn't have that function
    pass
  try:
    return eval("%s('%s')"%(converter,value))
  except:
    pass
  return value


class DynamicConfig(socorro_config.Config):
  """
  This adds to Config the possibility of dynamically updating our internal state based on an external change

  The mechanism for doing this is to imbue self with a function that knows how to get current data, and then at the
  appropriate moment, call that function.

  You may also imbue self with a function that accepts a Config, alters its internal state and hands it back.

  Usage notes:
    - You may use DynamicConfig exactly as you now use Config
    - When you wish to make use of the dynamic aspects, you may wish to:
      = Store all 'calculable' values in this DynamicConfig instance, so your own file need not be aware of updates
      = Provide a function fn: self.reEvaluateFunction = fn, that can be used to re-evaluate these calculable values
      = Make sure your own code looks only to this instance for values strictly dependent on config data:
         - Do not save values calculable from config data except in the config instance
         - Or always recalculate such values on the fly
      = Consider naming dynamically-alterable keys in a stylized manner (Apps Hungarian Notation:
        http://www.joelonsoftware.com/articles/Wrong.html)
    - Updates can happen in any of three ways:
      = Checks the current time against the next periodic update time, calls self.doUpdate() if due or overdue
        -- Only if self.updateInterval is a non-zero positive interval
      = Accepts a signal which causes a call to self.doUpdate() for each instance with that signal number
      = You can call dynConfigInstance.doUpdate() NOTE: not named 'update' which would hide dict.update() method
  """
  instances = {}
  def __init__(self,*args,**kwargs):
    """
    Passes appropriate kwargs to Config, pays local attention to these keys:
    updateInterval: default: '0' format: 'dd:hh:mm:ss', leading parts optional. Must be >= 0 seconds.
    updateFunction: default: noop(). Takes self as argument. Behavior: Updates default values in argument
    reEvaluateFunction: default: noop(). Takes self as argument. Behavior: Mutates values in argument
    signalNumber: default: SIGALRM (14). If 0, then signals will not be handled.
      Instances that share the same signalNumber will all be update()-ed at every signal.

    self.internal.updateFunction may be set after construction if desired: Avoids double-work at construction
    self.internal.reEvalutateFunction may be set after construction if desired, but this is not recommended.
    """
    skwargs = dict([(x,kwargs[x]) for x in socorro_config.getDefaultedConfigOptions().keys() if x in kwargs])
    for i in range(len(args)):
      skwargs[socorro_config.namedConfigOptions[i]] = args[i]
    super(DynamicConfig,self).__init__(**skwargs)
    self.internal.updateFunction = kwargs.get('updateFunction',noop)
    self.internal.reEvaluateFunction = kwargs.get('reEvaluateFunction',noop)
    self.internal.signalNumber = kwargs.get('signalNumber',14)
    self.internal.nextUpdate = None
    updateInterval = kwargs.get('updateInterval','0:0:0:0')
    self.internal.updateDelta = socorro_config.timeDeltaConverter(updateInterval)
    if self.internal.updateDelta:
      if self.internal.updateDelta < datetime.timedelta(0):
        raise ValueError("updateInterval must be non-negative, but %s"%self.internal.updateDelta)
      self.internal.nextUpdate = utc_now() + self.internal.updateDelta

    # finally: make sure we are current
    if self.internal.signalNumber:
      priorSignal = signal.signal(self.internal.signalNumber,DynamicConfig.handleAlarm)
    self.doUpdate()
    DynamicConfig.instances[id(self)] = self

  def get(self,name,alt=None):
    try:
      return self.__getitem__(name)
    except:
      return alt

  def __getattr__(self, name):
    self.maybeUpdate()
    return super(DynamicConfig,self).__getattr__(name)

  def __getitem__(self, name):
    self.maybeUpdate()
    return super(DynamicConfig,self).__getitem__(name)

  def maybeUpdate(self):
    try:
      nu = self.internal.nextUpdate
      if nu:
        now = utc_now()
        if now >= nu:
          DynamicConfig.doUpdate(self) # as does this line
          self.internal.nextUpdate = now + self.internal.updateDelta
    except AttributeError: # We are probably looking something up during __init__
      pass

  def doUpdate(self):
    self.internal.updateFunction(self)
    self.internal.reEvaluateFunction(self)

  def close(self):
    """unregister self so handleAlarm() doesn't try something bad"""
    try:
      del(DynamicConfig.instances[id(self)])
    except KeyError:
      pass

  def __del__(self):
    self.close()

  @staticmethod
  def handleAlarm(signalNumber, frame):
    for id,dyC in DynamicConfig.instances.items():
      try:
        if dyC.internal.signalNumber == signalNumber:
          dyC.doUpdate() # multiple instances get done too much. Don't care
      except: # Don't really care what problem is: Give up immediately
        pass

