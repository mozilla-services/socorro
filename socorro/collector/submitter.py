#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import time as tm
import json
import os
import signal

import socorro.lib.util as sutil
import socorro.lib.iteratorWorkerFramework as iwf
import socorro.external.filesystem.filesystem as sfs
import socorro.lib.stats as stats

import poster
import urllib2

existingHangIdCache = {}

#-------------------------------------------------------------------------------
def doSubmission (formData, binaryFilePathName, url, logger=sutil.FakeLogger(), posterModule=poster):
    fields = dict([(t[0],t[1]) for t in formData.items()])
    fields['upload_file_minidump'] = open(binaryFilePathName, 'rb')
    datagen, headers = posterModule.encode.multipart_encode(fields);
    request = urllib2.Request(url, datagen, headers)
    print urllib2.urlopen(request).read(),
    try:
        logger.debug('submitted %s', formData['uuid'])
    except KeyError:
        logger.debug('submitted unknown')

#-------------------------------------------------------------------------------
def submissionDryRun (formData, binaryFilePathName, url):
    print formData['ProductName'], formData['Version']

#-------------------------------------------------------------------------------
def createSubmitterFunction (config):
    statsPools = config.statsPool
    def func (paramsTuple):
        jsonFilePathName, binaryFilePathName = paramsTuple[0]
        with open(jsonFilePathName) as jsonFile:
            formData = json.load(jsonFile)
        if config.uniqueHang:
            try:
                if formData['HangId'] in existingHangIdCache:
                    formData['HangId'] = existingHangIdCache
                else:
                    formData['HangId'] =  \
                    existingHangIdCache[formData['HangId']] = uuid.uuid4()
            except Exception:
                pass
        processTimeStatistic = statsPools.processTime.getStat()
        submittedCountStatistic = statsPools.submittedCount.getStat()
        try:
            processTimeStatistic.start()
            config.submissionFunc(formData, binaryFilePathName, config.url,
                                  config.logger)
            submittedCountStatistic.increment()
        except Exception:
            sutil.reportExceptionAndContinue(sutil.FakeLogger())
            failureCountStatistic = statsPools.failureCount.getStat()
            failureCountStatistic.increment()
            return iwf.OK
        finally:
            processTimeStatistic.end()
        return iwf.OK
    return func

#-------------------------------------------------------------------------------
def createFileSystemIterator (config,
                              timeModule=tm,
                              fsModule=sfs):
    def anIter():
        for aPath, aFileName, aJsonPathName in \
            fsModule.findFileGenerator(config.searchRoot,
                                       lambda x: x[2].endswith("json")):
            dumpfilePathName = os.path.join(aPath, "%s%s" %
                                            (aFileName[:-5], ".dump"))
            yield (aJsonPathName, dumpfilePathName)
            if config.sleep:
                timeModule.sleep(config.sleep)
    return anIter

#-------------------------------------------------------------------------------
def createInfiniteFileSystemIterator (config,
                                      timeModule=tm):
    anIterator = createFileSystemIterator(config,
                                          timeModule)
    def infiniteIterator():
        while True:
            for x in anIterator():
                yield x
    # Why not use itertools.cycle?  Two reasons.  The IteratorWorkerFramework
    # has a design flaw where it wants a funciton that produces an iterator,
    # rather than an actual iterator.  itertool.cycle only deals with real
    # iterators not iterator factories.  Second, the cycle function caches all
    # the values from the first run of the target iterator.  It then serves out
    # the cached values for subsequent runs.  If the original iterator produces
    # a huge number of values, the cache will also be huge.  I'm avoiding that.
    return infiniteIterator

#-------------------------------------------------------------------------------
def createLimitedFileSystemIterator (config,
                                     timeModule=tm):
    anIterator = createInfiniteFileSystemIterator(config,
                                                  timeModule)
    def limitedIterator():
        for i, x in enumerate(anIterator()):
            if i >= config.numberOfSubmissions:
                break
            yield x
    return limitedIterator

#-------------------------------------------------------------------------------
def submitter (config):
    logger = config.logger
    signal.signal(signal.SIGTERM, iwf.respondToSIGTERM)
    signal.signal(signal.SIGHUP, iwf.respondToSIGTERM)

    statsPool = sutil.DotDict(
        { 'submittedCount': stats.CounterPool(config),
          'failureCount': stats.CounterPool(config),
          'processTime': stats.DurationAccumulatorPool(config),
        })
    config.statsPool = statsPool

    reportigCounter = 0
    def statsReportingWaitingFunc():
        if not statsReportingWaitingFunc.reportingCounter % 60:
            submittedCountPool = statsPool.submittedCount
            numberOfMinutes = submittedCountPool.numberOfMinutes()
            if numberOfMinutes:
                logger.info('running for %d minutes', numberOfMinutes)
                numberSubmitted = submittedCountPool.read()
                logger.info('average submitted per minute: %s', \
                      (float(numberSubmitted) / numberOfMinutes))
                numberOfFailures = statsPool.failureCount.read()
                logger.info('failures in the last five minutes: %d', \
                      numberOfFailures)
                processTime = statsPool.processTime.read()
                logger.info('average time in last five minutes: %s', \
                      processTime)
        statsReportingWaitingFunc.reportingCounter += 1
    statsReportingWaitingFunc.reportingCounter = 0

    theIterator = config.iteratorFunc (config)
    theWorkerFunction = createSubmitterFunction(config)

    submissionMill = iwf.IteratorWorkerFramework(config,
                                                 jobSourceIterator=theIterator,
                                                 taskFunc=theWorkerFunction,
                                                 name='submissionMill')

    try:
        submissionMill.start()
        submissionMill.waitForCompletion(statsReportingWaitingFunc)
            # though, it only ends if someone
            # hits ^C or sends SIGHUP or SIGTERM
            # - any of which will get translated
            # into a KeyboardInterrupt exception
    except KeyboardInterrupt:
        while True:
            try:
                submissionMill.stop()
                break
            except KeyboardInterrupt:
                logger.warning('We heard you the first time.  There is no need '
                               'for further keyboard or signal interrupts.  We '
                               'are waiting for the worker threads to stop.  '
                               'If this app does not halt soon, you may have '
                               'to send SIGKILL (kill -9)')


if __name__ == '__main__':
  """This is the original submitter.py code.  It can still be used as an
  executeable."""
  try:
    import json
  except ImportError:
    import simplejson as json
  import sys
  import uuid
  import socorro.external.filesystem.filesystem

  existingHangIdCache = {}
  poster.streaminghttp.register_openers()

  def submitCrashReport (jsonFilePathName, binaryFilePathName, serverURL, uniqueHang):
    jsonFile = open(jsonFilePathName)
    try:
      data = json.load(jsonFile)
    finally:
      jsonFile.close()

    if uniqueHang:
      try:
        if data['HangId'] in existingHangIdCache:
          data['HangId'] = existingHangIdCache
        else:
          data['HangId'] = existingHangIdCache[data['HangId']] = uuid.uuid4()
      except:
        pass

    fields = dict([(t[0],t[1]) for t in data.items()])
    fields['upload_file_minidump'] = open(binaryFilePathName, 'rb')
    datagen, headers = poster.encode.multipart_encode(fields);
    request = urllib2.Request(serverURL, datagen, headers)
    print urllib2.urlopen(request).read(),

  def reportErrorToStderr (x):
    print >>sys.stderr, x

  def walkFileSystemSubmittingReports (fileSystemRoot, serverURL, errorReporter=reportErrorToStderr, uniqueHang=False):
    for aPath, aFileName, aJsonPathName in socorro.external.filesystem.filesystem.findFileGenerator(fileSystemRoot, lambda x: x[2].endswith("json")):
      try:
        dumpfilePathName = os.path.join(aPath, "%s%s" % (aFileName[:-5], ".dump"))
        submitCrashReport(aJsonPathName, dumpfilePathName, serverURL, uniqueHang)
      except KeyboardInterrupt:
        break
      except Exception, x:
        errorReporter(x)

  import socorro.lib.ConfigurationManager

  import os.path
  import traceback

  def myErrorReporter (anException):
    print >>sys.stderr, type(anException), anException
    exceptionType, exception, tracebackInfo = sys.exc_info()
    traceback.print_tb(tracebackInfo, None, sys.stderr)

  commandLineOptions = [
    ('c',  'config', True, './config', "the config file"),
    ('u',  'url', True, 'https://crash-reports.stage.mozilla.com/submit', "The url of the server to load test"),
    ('j',  'jsonfile', True, None, 'the pathname of a json file for POST'),
    ('d',  'dumpfile', True, None, 'the pathname of a dumpfile to upload with the POST'),
    ('s',  'searchRoot', True, None, 'a filesystem location to begin a search for json/dump combos'),
    ('i',  'uniqueHangId', False, None, 'coche and uniquify hangids'),
    ]

  config = socorro.lib.ConfigurationManager.newConfiguration(configurationOptionsList=commandLineOptions)

  uniqueHang = 'uniqueHangId' in config

  if config.searchRoot:
    walkFileSystemSubmittingReports(config.searchRoot, config.url, myErrorReporter, uniqueHang)
  else:
    try:
      submitCrashReport(config.jsonfile, config.dumpfile, config.url, uniqueHang)
    except Exception, x:
      myErrorReporter(x)

