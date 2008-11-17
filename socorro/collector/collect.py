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

compiledRegularExpressionType = type(re.compile(''))
functionType = type(lambda x: x)

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
  def throttle (self, json):
    #print processedThrottleConditions
    for key, condition, percentage in self.processedThrottleConditions:
      #print "testing  %s %s %d" % (key, condition, percentage)
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
