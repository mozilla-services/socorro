#
# collect.py, collector functions for Pylons, CGI, and mod_python collectors
#

try:
  import socorro.lib.uuid as uuid
except ImportError:
  import uuid

import socorro.lib.ooid as ooid

import os, cgi, sys, tempfile, simplejson
import datetime as dt
import time as tm
import re
import random
import logging
logger = logging.getLogger("collector")

compiledRegularExpressionType = type(re.compile(''))
functionType = type(lambda x: x)

pattern_str = r'(\d+)\.(\d+)\.?(\d+)?\.?(\d+)?([a|b]?)(\d*)(pre)?(\d)?'
pattern = re.compile(pattern_str)

pattern_plus = re.compile(r'((\d+)\+)')


#=================================================================================================================
class Collect(object):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, configurationContext):
    self.config = configurationContext
    self.processedThrottleConditions = self.preprocessThrottleConditions(self.config.throttleConditions)

  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def regexpHandlerFactory(regexp):
    def egexpHandler(x):
      return regexp.search(x)
    return egexpHandler

  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def boolHandlerFactory(aBool):
    def boolHandler(dummy):
      return aBool
    return boolHandler

  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def genericHandlerFactor(anObject):
    def genericHandler(x):
      return anObject == x
    return genericHandler

  #-----------------------------------------------------------------------------------------------------------------
  def preprocessThrottleConditions(self, originalThrottleConditions):
    newThrottleConditions = []
    for key, condition, percentage in originalThrottleConditions:
      #print "preprocessing %s %s %d" % (key, condition, percentage)
      conditionType = type(condition)
      if conditionType == compiledRegularExpressionType:
        #print "reg exp"
        newCondition = Collect.regexpHandlerFactory(condition)
        #print newCondition
      elif conditionType == bool:
        #print "bool"
        newCondition = Collect.boolHandlerFactory(condition)
        #print newCondition
      elif conditionType == functionType:
        newCondition = condition
      else:
        newCondition = Collect.genericHandlerFactor(condition)
      newThrottleConditions.append((key, newCondition, percentage))
    return newThrottleConditions

  #-----------------------------------------------------------------------------------------------------------------
  def terminated (self, json):
    return False

  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def normalizeVersionToInt(version_string):
    # replace \d+\+ with $1++
    match = re.search(pattern_plus, version_string)
    if match:
      (old, ver) = match.groups()
      replacement = "%dpre0"%(int(ver)+1)
      version_string = version_string.replace(old, replacement)

    # version_string.replace()
    match = re.match(pattern, version_string)
    if match:
      (major, minor1, minor2, minor3, alpha, alpha_n, pre, pre_n) = match.groups()

      # normalize data
      major  = int(major)
      minor1 = int(minor1)
      if not minor2:
        minor2 = 0
      else:
        minor2 = int(minor2)

      if not minor3:
        minor3 = 0
      else:
        minor3 = int(minor3)

      if alpha == 'a':
        alpha = 0
      elif alpha == 'b':
        alpha = 1
      else:
        alpha = 2

      if alpha_n:
        alpha_n  = int(alpha_n)
      else:
        alpha_n = 0

      if pre == 'pre':
        pre = 0
      else:
        pre = 1

      if pre_n:
        pre_n = int(pre_n)
      else:
        pre_n = 0

      # print (major,minor1,minor2,alpha,alpha_n,pre,pre_n)
      # print version_string
      int_str = "%02d%02d%02d%02d%d%02d%d%02d"  % (major, minor1, minor2, minor3, alpha, alpha_n, pre, pre_n)

      return int(int_str)

  #-----------------------------------------------------------------------------------------------------------------
  def understandsRefusal (self, json):
    try:
      #logger.debug('understandsRefusal - %s, %s, %s, %s, %s', json['ProductName'], json['Version'], self.config.minimalVersionForUnderstandingRefusal[json['ProductName']], Collect.normalizeVersionToInt(json['Version']), Collect.normalizeVersionToInt(self.config.minimalVersionForUnderstandingRefusal[json['ProductName']]))
      return Collect.normalizeVersionToInt(json['Version']) >= Collect.normalizeVersionToInt(self.config.minimalVersionForUnderstandingRefusal[json['ProductName']])
    except KeyError:
      return False

  #-----------------------------------------------------------------------------------------------------------------
  def throttle (self, json):
    #print processedThrottleConditions
    for key, condition, percentage in self.processedThrottleConditions:
      #print "testing  %s %s %d" % (key, condition, percentage)
      throttleMatch = False
      try:
        throttleMatch = condition(json[key])
      except KeyError:
        if key == None:
          throttleMatch = condition(None)
        else:
          #print "bad key"
          continue
      except IndexError:
        pass
      if throttleMatch:
        randint = random.randint(0, 100)
        #print "throttle: %d %d %s" % (randint, percentage, randint > percentage)
        return randint > percentage
    return True

  #-----------------------------------------------------------------------------------------------------------------
  #def generateUuid (self, jsonDataDictionary):
    #newUuid = str(uuid.uuid4())
    #date = dt.datetime(*tm.localtime(jsonDataDictionary["timestamp"])[:3])
    #return "%s%1d%2d%02d%02d" % (newUuid[:-7], self.config.storageDepth, date.year, date.month, date.day)

  #-----------------------------------------------------------------------------------------------------------------
  def storeDump(self, dumpInputStream, fileHandleOpenForWriting):
    """Stream the uploaded dump to the open file handle"""
    # XXXsayrer need to peek at the first couple bytes for a sanity check
    # breakpad leading bytes: 0x504d444d
    while 1:
      data = dumpInputStream.read(4096)
      if not data:
        break
      fileHandleOpenForWriting.write(data)

  #-----------------------------------------------------------------------------------------------------------------
  def makeJsonDictFromForm (self, form):
    names = [name for name in form.keys() if name != self.config.dumpField]
    jsonDict = {}
    for name in names:
      if type(form[name]) == str:
        jsonDict[name] = form[name]
      else:
        jsonDict[name] = form[name].value
    jsonDict["timestamp"] = tm.time()
    return jsonDict

  #-----------------------------------------------------------------------------------------------------------------
  def storeJson(self, jsonDataDictionary, fileHandleOpenForWriting):
    simplejson.dump(jsonDataDictionary, fileHandleOpenForWriting)
