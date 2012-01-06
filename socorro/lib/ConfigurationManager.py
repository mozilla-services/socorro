#!/usr/bin/python
#
# Copyright 2004 by Centaur Software Engineering, Inc.
#
#
#    This file is part of The CSE Python Library.
#
#    The CSE Python Library is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    The CSE Python Library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with The CSE Python Library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#


version = "1.3"

import getopt
import os
import sys
import cStringIO
import datetime

from socorro.lib.datetimeutil import string_to_datetime

#============================================================================================
class ConfigFileMissingError (IOError):
  pass
ConfigurationManagerConfigFileMissing = ConfigFileMissingError  # for legacy compatability
#============================================================================================
class ConfigFileOptionNameMissingError (Exception):
  pass
ConfigurationManagerConfigFileOptionNameMissing = ConfigFileOptionNameMissingError  # for legacy compatability
#============================================================================================
class NotAnOptionError (Exception):
  pass
ConfigurationManagerNotAnOption = NotAnOptionError   # for legacy compatability

#============================================================================================
class OptionError (Exception):
  def __init__(self, errorString):
    super(OptionError, self).__init__(errorString)

#============================================================================================
class CannotConvert (ValueError):
  pass

#============================================================================================
class Option(object):
  pass

class Internal(object):
  pass

def getDefaultedConfigOptions():
  """
  Used in Config subclass so as to pass only appropriate args to its super()
  Is a function as a way to decouple the empty configurationOptionsList from prior invocations
  """
  return {
    'configurationOptionsList':[],
    'optionNameForConfigFile':'config',
    'configurationFileRequired':False,
    'configurationModule':None,
    'automaticHelp':True,
    'applicationName':'',
    'helpHandler':None,
    }

namedConfigOptions = [
  'configurationOptionsList',
  'optionNameForConfigFile',
  'ConfigurationFileRequired',
  'configurationModule',
  'automaticHelp',
  'applicationName',
  'helpHandler',
  ]

#------------------------------------------------------------------------------------------
def newConfiguration(**kwargs):
  """ This used as an alternate constructor for class Config so that applications can
      be lax in defining all the required paramters in the right order.
  """
  kw = getDefaultedConfigOptions()
  kw.update(kwargs)
  return Config(**kw)

 #============================================================================================
class Config (dict):
  """This class encapsulates the process of getting command line arguments, configuration files and environment variables into a program.
  It wraps the Python getopt module and provides a more comprehensive interface.
  """

  #------------------------------------------------------------------------------------------
  def __init__ (self, configurationOptionsList=[], optionNameForConfigFile="config", configurationFileRequired=False, configurationModule=None, automaticHelp=False, applicationName='', helpHandler=None):
    """Initialize a new instance.

    Input Parameters:
      configurationOptionsList: a list of tuples that represent the options available to the user.  The tuples take this form:
        (singleCharacterOptionForm, longOptionForm, takesParametersBoolean, defaultValue, humanReadableOptionExplanation [, optionalListOfOptionParameterPairs | conversionFunction ])
        The optionalListOfOptionParameterPairs to create short cuts for sets of options.  The form is a list of two element tuples specifying some other option
        and its value.  Examples can be seen below.
        conversionFunction is a function that will take a string and convert it to the target type needed for the parameter
      optionNameForConfigFile: the name of the option that stores the pathname of the configuration file - if this is set to None then we assume there
        is no configuration file and one will not be tried
      configurationFileRequired: if True, the lack of a configuration file is considered a fatal error
    """
    self.internal = Internal()
    self.internal.originalConfigurationOptionsList = configurationOptionsList
    self.internal.applicationName = applicationName
    # incorporate config options from configuration module
    try:
      for key, value in configurationModule.__dict__.items():
        if type(value) == Option:
          optionDefinition = []
          try:
            optionDefinition.append(value.singleCharacter) #0
          except AttributeError:
            optionDefinition.append(None)
          optionDefinition.append(key) #1
          optionDefinition.append(True) #2
          try:
            optionDefinition.append(value.default) #3
          except AttributeError:
            optionDefinition.append(None)
          try:
            optionDefinition.append(value.doc) #4
          except AttributeError:
            optionDefinition.append("%s imported from %s" % (key, configurationModule.__name__))
          try:
            optionDefinition.append(value.fromStringConverter) #5
          except AttributeError:
            pass
          configurationOptionsList.append(optionDefinition)
        else:
          if key[:2] != "__" and type(value) != type(os):
            configurationOptionsList.append([None, key, True, value, "%s imported from %s" % (key, configurationModule.__name__)])
    except AttributeError:
      pass #we're apparently not using an initialization module

    self.internal.singleLetterCommandLineOptionsForGetopt = ""
    self.internal.expandedCommandLineOptionsForGetopt = []

    self.internal.allowableOptionDictionary = {}
    self.internal.allowableLongFormOptionDictionary = {}
    for x in configurationOptionsList:
      if x[0]:
        self.internal.allowableOptionDictionary[x[0]] = x
      self.internal.allowableOptionDictionary[x[1]] = self.internal.allowableLongFormOptionDictionary[x[1]] = x
      self.__addOptionsForGetopt(x)

    # add autohelp if needed
    if automaticHelp and ("help" not in self.internal.allowableLongFormOptionDictionary):
      helpOptionTuple = ('?', 'help', False, None, 'print this list')
      configurationOptionsList.append(helpOptionTuple)
      self.internal.allowableOptionDictionary[helpOptionTuple[0]] = helpOptionTuple
      self.internal.allowableOptionDictionary[helpOptionTuple[1]] = self.internal.allowableLongFormOptionDictionary[helpOptionTuple[1]] = helpOptionTuple
      self.__addOptionsForGetopt(helpOptionTuple)

    # handle help requests appropriately
    self.internal.helpHandler = self.__nothingHelpHandler # default is no autohelp
    if helpHandler:                              # if user handed us one, use it
      self.internal.helpHandler = helpHandler
    elif "help" in self.internal.allowableLongFormOptionDictionary: # if needed, use default
      self.internal.helpHandler = self.__defaultHelpHandler

    # setup all defaults for options:
    for x in configurationOptionsList:
      #if x[2] and x[3] is not None:
      if x[2]:
        self[x[1]] = x[3]

    # get options from the environment - these override defaults
    for x in os.environ:
      if self.internal.allowableOptionDictionary.has_key(x):
        self[self.internal.allowableOptionDictionary[x][1]] = os.environ.get(x)
        self.__insertCombinedOption(x, self)

    # get the options from the command line - these will eventually override all other methods of setting options
    try:
      options, ignoreArgs = getopt.getopt(sys.argv[1:], self.internal.singleLetterCommandLineOptionsForGetopt, self.internal.expandedCommandLineOptionsForGetopt)
    except getopt.GetoptError, e:
      pass  #TODO - temporary measure
      #raise NotAnOptionError, e
    commandLineEnvironment = {} # save these options for merging later
    for x in options:
      if len(x[0]) == 2: #single letter option
        longFormOfSingleLetterOption = self.internal.allowableOptionDictionary[x[0][1]][1]
        if self.internal.allowableOptionDictionary[longFormOfSingleLetterOption][2]:
          commandLineEnvironment[longFormOfSingleLetterOption] = x[1]
        else:
          commandLineEnvironment[longFormOfSingleLetterOption] = None
        self.__insertCombinedOption(longFormOfSingleLetterOption, commandLineEnvironment)
      else:
        longFormOption = x[0][2:]
        if self.internal.allowableOptionDictionary[longFormOption][2]:
          commandLineEnvironment[longFormOption] = x[1]
        else:
          commandLineEnvironment[longFormOption] = None
        self.__insertCombinedOption(longFormOption, commandLineEnvironment)

    # get any options from the config file
    # any options already set in the environment are overridden
    if optionNameForConfigFile is not None:
      configFile = None
      try:
        try:
          try:
            configFile = open(commandLineEnvironment[optionNameForConfigFile], 'r')
          except KeyError:
            configFile = open(self[optionNameForConfigFile], 'r')
          except IOError, e:
            raise ConfigFileMissingError()
          for x in configFile:
            x = x.strip()
            if not x or x[0] == '#' : continue
            key,value = x.split('=', 1)
            key = key.rstrip()
            if not key: continue
            value = value.lstrip()
            if self.internal.allowableOptionDictionary.has_key(key):
              longFormOption = self.internal.allowableOptionDictionary[key][1]
              self.__insertCombinedOption(longFormOption, self)
              try:
                self[longFormOption] = value
              except IndexError:
                self[longFormOption] = None
            else:
              raise NotAnOptionError, "option '%s' in the config file is not recognized" % key
        except KeyError,x:
          if configurationFileRequired:
            raise ConfigFileOptionNameMissingError()
        except IOError:
          if configurationFileRequired:
            raise ConfigFileMissingError()
      finally:
        if configFile: configFile.close()

    # merge command line options with the workingEnvironment
    # any options already specified in the environment or
    # configuration file are overridden.
    for x in commandLineEnvironment:
      self[x] = commandLineEnvironment[x]

    # mix in combo commandline arguments
    for optionTuple in self.internal.allowableLongFormOptionDictionary.values():
      try:
        if type(optionTuple[5]) == list and optionTuple[1] in self:
          for longFormOptionFromCombo, valueFromCombo in optionTuple[5]:
            self[longFormOptionFromCombo] = valueFromCombo
      except IndexError:
        pass #not a combo option

    # make sure that non-string values in the workingEnvironment
    # have the right type.  Assume the default value has the right
    # type and cast the existing value to that type iff no conversion
    # function was supplied
    for optionTuple in self.internal.allowableLongFormOptionDictionary.values():
      try:
        conversionFunction = optionTuple[5]
      except IndexError:
        conversionFunction = type(optionTuple[3])
      if conversionFunction not in (str, list, type(None)):
        try:
          self[optionTuple[1]] = conversionFunction(self[optionTuple[1]])
        except (KeyError, TypeError):
          pass
        except ValueError, x:
          raise CannotConvert(str(x))

    # do help (auto or otherwise)
    if 'help' in self:
      self.internal.helpHandler(self)

  #------------------------------------------------------------------------------------------
  def __nothingHelpHandler(self, config):
    pass

  #------------------------------------------------------------------------------------------
  def __defaultHelpHandler(self, config):
    if self.internal.applicationName:
      print >>sys.stderr, self.internal.applicationName
    self.outputCommandSummary(sys.stderr, 1)
    sys.exit()

  #------------------------------------------------------------------------------------------
  def __addOptionsForGetopt (self, optionTuple):
    """Internal Use - during setup, this function sets up internal structures with a new optionTuple.

    Parameters:
      optionTuple: a tuple of the form - (singleCharacterOptionForm, longOptionForm, takesParametersBoolean, ...)
    """
    if optionTuple[2]: #does this option have parameters?
      if optionTuple[0]:
        self.internal.singleLetterCommandLineOptionsForGetopt = "%s%s:" % (self.internal.singleLetterCommandLineOptionsForGetopt, optionTuple[0])
      self.internal.expandedCommandLineOptionsForGetopt.append("%s=" % optionTuple[1])
    else:
      if optionTuple[0]:
        self.internal.singleLetterCommandLineOptionsForGetopt = "%s%s" % (self.internal.singleLetterCommandLineOptionsForGetopt, optionTuple[0])
      self.internal.expandedCommandLineOptionsForGetopt.append(optionTuple[1])

  #------------------------------------------------------------------------------------------
  def __insertCombinedOption (self, anOption, theDictionaryToInsertInto):
    """Internal Use - during setup, maybe set short-cut option(s) from the allowableOptionDictionary

    Parameters:
      option: key into the allowableOptionDictionary
    Action:
      If the key is found, look for optional (key,value) pairs that define this option as a short-cut for one or more defaults.
      For each short-cut found, set the short-cut key and value in the given dictionary.
    """
    try:
      for x in self.internal.allowableOptionDictionary[anOption][5]:
        theDictionaryToInsertInto[x[0]] = x[1]
    except (KeyError, IndexError, TypeError) :
      pass

  #------------------------------------------------------------------------------------------
  def dumpAllowableOptionDictionary(self):
    """ for debugging and understanding what the heck is going on
    """
    try:
      for k in self.internal.allowableOptionDictionary.keys():
        v = self.internal.allowableOptionDictionary.get(k)
        print "%-8s (%d) %s" % (k,len(v),str(v))
    except:
      print 'No dictionary available'

  #------------------------------------------------------------------------------------------
  def outputCommandSummary (self, outputStream=sys.stdout, sortOption=0, outputTemplateForOptionsWithParameters="--%s\n\t\t%s (default: %s)",
                                                                         outputTemplateForOptionsWithoutParameters="--%s\n\t\t%s",
                                                                         outputTemplatePrefixForSingleLetter="\t-%s, ",
                                                                         outputTemplatePrefixForNoSingleLetter="\t    "):
    """outputs the list of acceptable commands.  This is useful as the output of the 'help' option or usage.

    Parameters:
      outputStream: where to send the output
      sortOption: 0 - sort by the single character option
                  1 - sort by the long option
      outputTemplateForOptionsWithParameters: a string template for outputing options that have parameters from the long form onward
      outputTemplateForOptionsWithoutParameters: a string template for outputing options that have no parameters from the long form onward
      outputTemplatePrefixForSingleLetter: a string template for the first part of a listing where there is a single letter form of the command
      outputTemplatePrefixForNo: a string template for the first part of a listing where there is no single letter form of the command
    """
    optionsList = [ x for x in self.internal.originalConfigurationOptionsList ]
    optionsList.sort(lambda a, b: (a[sortOption] > b[sortOption]) or -(a[sortOption] < b[sortOption]))
    for x in optionsList:
      if x[0]:
        prefix = outputTemplatePrefixForSingleLetter
        commandTuple = (x[0], x[1], x[4], x[3])
      else:
        prefix = outputTemplatePrefixForNoSingleLetter
        commandTuple = (x[1], x[4], x[3])
      if x[2]:
        print >>outputStream, ("%s%s" % (prefix, outputTemplateForOptionsWithParameters)) % commandTuple
      else:
        print >>outputStream, ("%s%s" % (prefix, outputTemplateForOptionsWithoutParameters)) % commandTuple[:-1]

  #------------------------------------------------------------------------------------------
  def output (self, outputStream=sys.stdout, outputTemplateForOptionsWithParameters="\t%s=%s", outputTemplateForOptionsWithoutParameters="\t%s", blockPassword=True):
    """this routine will write the current values of all options to an output stream.

    Parameters:
      outputStream: where to write the output
      outputTemplateForOptionsWithParameters: a string template for outputing options that have parameters
      outputTemplateForOptionsWithoutParameters: a string template for outputing options that have no parameters
      blockPassword: a boolean controlling the output of options that have the string 'password' in their name
        True - the value will be printed as **********
        False - the value will print normally
    """
    environmentList = [x for x in self.iteritems() ]
    environmentList.sort(lambda x, y: (x[0] > y[0]) or -(x[0] < y[0]))
    for x in environmentList:
      if blockPassword and x[1] is not None and "password" in x[0].lower():
        print >>outputStream, outputTemplateForOptionsWithParameters % (x[0], "*" * 10)
        continue
      if x[1] is not None:
        print >>outputStream, outputTemplateForOptionsWithParameters % x
      else:
        print >>outputStream, outputTemplateForOptionsWithoutParameters % x[0]

  #------------------------------------------------------------------------------------------
  def __str__ (self):
    """ return a string representation of the options and their states.
    """
    stringio = cStringIO.StringIO()
    self.output(stringio)
    s = stringio.getvalue()
    stringio.close()
    return s

  #------------------------------------------------------------------------------------------
  def __getattr__(self, name):
    """ this function implements an interface allowing the entries in the dictionary
        to be accessed using the dot operator:  self["fred"] == self.fred
    """
    try:
      return self[name]
    except KeyError, x:
      raise AttributeError(x)

ConfigurationManager = Config #for legacy compatibility

#------------------------------------------------------------------------------------------
def ioConverter(inputString):
  """ a conversion function for to select stdout, stderr or open a file for writing
  """
  if type(inputString) is str:
    lowerInputString = inputString.lower()
    if lowerInputString == 'stdout':
      return sys.stdout
    if lowerInputString == 'stderr':
      return sys.stderr
    return open(inputString, "w")
  return inputString

#------------------------------------------------------------------------------------------
def dateTimeConverter(inputString):
  """ a conversion function for datetimes
  """
  return string_to_datetime(inputString)

#------------------------------------------------------------------------------------------
def timeDeltaConverter(inputString):
  """ a conversion function for time deltas
  """
  if type(inputString) is str:
    days,hours,minutes,seconds = 0,0,0,0
    details = inputString.split(':')
    if len(details) >= 4:
      days = int(details[-4])
    if len(details) >= 3:
      hours = int(details[-3])
    if len(details) >= 2:
      minutes = int(details[-2])
    if len(details) >= 1:
      seconds = int(details[-1])
    return datetime.timedelta(days = days, hours = hours, minutes = minutes, seconds = seconds)
  return inputString


#------------------------------------------------------------------------------------------
def booleanConverter(inputString):
  """ a conversion function for boolean
  """
  if type(inputString) is str:
    return inputString.lower() in ("true", "t", "1")
  return inputString

#-------------------------------------------------------------------------------
def classConverter(input_str):
    """ a conversion that will import a module and class name
    """
    parts = input_str.split('.')
    try:
        # first try as a complete module
        package = __import__(input_str)
    except ImportError, x:
        if len(parts) == 1:
            # maybe this is a builtin
            return eval(input_str)
        # it must be a class from a module
        package = __import__('.'.join(parts[:-1]), globals(), locals(), [])
    obj = package
    for name in parts[1:]:
        obj = getattr(obj, name)
    return obj


if __name__ == "__main__":

  def doubler (aString):
    return float(aString) * 2

  commandLineOptions = [ ('c', 'config', True, './config', "the config file"),
                         ('a', 'alpha', True, 600, "the alpha option takes an int"),
                         ('b', 'beta', True, 'hello', 'the beta option takes a string'),
                         ('g', 'gamma', False, None, "the gamma option accepts no parameter"),
                         ('f', 'floater', True, 3.1415, "the floater option"),
                         ('d', 'doubler', True, 3.1415, "the doubler option", doubler),
                         ('p', 'secretpassword', True, '', "the password - it won't print when listing configuration"),
                         ('o', 'ostream', True, 'stdout', 'output stream', ioConverter),
                         ('d', 'dt', True, '1960-05-04 15:10:00', 'aDateTime', dateTimeConverter),
                         ('l', 'timedelta', True, '123:11:16', 'output stream', timeDeltaConverter),
                         (None, 'noShort', False, None, 'only available as a long option'),
                         ('$', 'dollar', False, None, "combo of 'alpha=22, beta=10'", [ ("alpha", 22), ("beta", 10) ] ),
                         ('#', 'hash', False, None, "combo of 'alpha=2, beta=100, gamma, doubler=23'", [ ("alpha", 2), ("beta", 100), ("gamma", None), ("doubler", 23) ] ),
                       ]

  cm = newConfiguration(configurationOptionsList=commandLineOptions)

  print cm
  cm.dumpAllowableOptionDictionary()
#   print "AOPTDICT"
#   for k in cm.allowableOptionDictionary.keys():



  print cm.doubler
  print cm.secretpassword
  try:
    print cm.dollar
  except AttributeError:
    print "try running with the -$ option for more exciting fun"
  try:
    print cm.hash
  except AttributeError:
    print "try running with the -# option for more exciting fun"


  #import config
  #cm = newConfiguration(configurationModule=config)
  #print cm







