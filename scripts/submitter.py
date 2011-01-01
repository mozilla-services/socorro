#!/usr/bin/python

import time as tm
import datetime as dt
import json
import pycurl
import signal

import socorro.lib.iteratorWorkerFramework as iwf
import socorro.lib.filesystem as sfs
import socorro.lib.stats as stats


#-------------------------------------------------------------------------------
def doSubmission (formData, binaryFilePathName, url, pycurlModule=pycurl):
    print 'starting doSubmission'
    c = pycurlModule.Curl()
    fields = [(str(t[0]), str(t[1])) for t in formData.items()]
    fields.append (("upload_file_minidump",
                    (c.FORM_FILE, binaryFilePathName)))
    c.setopt(c.TIMEOUT, 60)
    c.setopt(c.POST, 1)
    c.setopt(c.URL, url)
    c.setopt(c.HTTPPOST, fields)
    c.perform()
    c.close()
    try:
        print 'submitted %s' % formData['uuid']
    except KeyError:
        print 'submitted unknown'

#-------------------------------------------------------------------------------
def submissionDryRun (formData, binaryFilePathName, url):
    #print formData['ProductName'], formData['Version']
    pass

#-------------------------------------------------------------------------------
def createSubmitterFunction (config):
    submissionFunc = config.submissionFunc
    statsPools = config.statsPool
    def func (paramsTuple):
        jsonFilePathName, \
        binaryFilePathName, \
        serverURL, \
        uniqueHang = paramsTuple[0]
        with open(jsonFilePathName) as jsonFile:
            formData = json.load(jsonFile)
        if uniqueHang:
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
            submissionFunc(formData, binaryFilePathName, serverURL)
            submittedCountStatistic.increment()
        except Exception:
            sutil.reportExceptionAndContinue(sutil.FakeLogger())
            failureCountStatistic = statsPools.failureCount.getStat()
            failureCountStatistic.increment()
            return iwf.ok
        finally:
            processTimeStatistic.end()
        return iwf.ok
    return func

#-------------------------------------------------------------------------------
def createFileSystemIterator (fileSystemRoot, serverURL,
                              sleep=0,
                              uniqueHang=False,
                              timeModule=tm):
    def anIter():
        for aPath, aFileName, aJsonPathName in \
            sfs.findFileGenerator(fileSystemRoot,
                                  lambda x: x[2].endswith("json")):
            dumpfilePathName = os.path.join(aPath, "%s%s" %
                                            (aFileName[:-5], ".dump"))
            yield (aJsonPathName, dumpfilePathName, config.url, uniqueHang)
            if sleep:
                timeModule.sleep(sleep)
    return anIter

#-------------------------------------------------------------------------------
def createInfiniteFileSystemIterator (fileSystemRoot, serverURL,
                                      sleep=0,
                                      uniqueHang=False,
                                      timeModule=tm):
    anIterator = createFileSystemIterator(fileSystemRoot, serverURL,
                                          sleep,
                                          uniqueHang,
                                          timeModule)
    def infiniteIterator():
        while True:
            for x in anIterator():
                yield x
                if sleep:
                    timeModule.sleep(sleep)
    return infiniteIterator

#-------------------------------------------------------------------------------
def createLimitedFileSystemIterator (fileSystemRoot, serverURL,
                                     sleep=0,
                                     uniqueHang=False,
                                     timeModule=tm):
    anIterator = createFileSystemIterator(fileSystemRoot, serverURL,
                                          sleep,
                                          uniqueHang,
                                          timeModule)
    def limitedIterator():
        i = 0
        while True:
            for x in anIterator():
                if n == maxIter:
                    break
                x += 1
                yield x
                if sleep:
                    timeModule.sleep(sleep)
            if n == maxIter:
                break
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
                print numberOfMinutes
                numberSubmitted = submittedCountPool.read()
                print 'average submitted per minute: %s' % \
                      (float(numberSubmitted) / numberOfMinutes)
                numberOfFailures = statsPool.failureCount.read()
                print 'failures in the last five minutes: %d' % \
                      numberOfFailures
                processTime = statsPool.processTime.read()
                print 'average time in last five minutes: %s' % \
                      processTime
        statsReportingWaitingFunc.reportingCounter += 1
    statsReportingWaitingFunc.reportingCounter = 0

    theIterator = config.iteratorFunc (config.searchRoot,
                                       config.url,
                                       config.sleep,
                                       'uniqueHangId' in config)
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

#-------------------------------------------------------------------------------
if __name__ == '__main__':
    import socorro.lib.ConfigurationManager as cm
    import socorro.lib.util as sutil

    import os.path
    import traceback

    commandLineOptions = [
      ('c',  'config', True, './config', "the config file"),
      ('u',  'url', True, 'https://crash-reports.stage.mozilla.com/submit',
                          "The url of the server to load test"),
      #('m',  'perMinute', True, 0, "the number of submissions per minutes to try (0 for max per minute)"),
      ('S',  'delay', True, 1, "pause between submission queing in milliseconds"),
      ('D',  'dryrun', False, None, "don't actually submit, just print product/version"),
      ('n',  'numberOfThreads', True, 4, 'the number of threads'),
      ('N',  'numberOfSubmissions', True, 'all',
             'the number items to submit (all, forever, 1...)'),
      ('j',  'jsonfile', True, None, 'the pathname of a json file for POST'),
      ('d',  'dumpfile', True, None,
             'the pathname of a dumpfile to upload with the POST'),
      ('s',  'searchRoot', True, None,
             'a filesystem location to begin a search for json/dump combos'),
      ('i',  'uniqueHangId', False, None, 'cache and uniquify hangids'),
      ]

    config = cm.newConfiguration(configurationOptionsList=commandLineOptions)

    print config.output()

    if config.numberOfSubmissions == 'forever':
        config.iteratorFunc = createInfiniteFileSystemIterator
    elif config.numberOfSubmissions == 'all':
        config.iteratorFunc = createFileSystemIterator
    else:
        config.iteratorFunc = createLimitedFileSystemIterator

    if 'dryrun' in config:
        config.submissionFunc = submissionDryRun
    else:
        config.submissionFunc = doSubmission

    config.sleep = float(config.delay)/1000.0

    config.logger = sutil.SilentFakeLogger()
    #config.logger = sutil.FakeLogger()

    uniqueHang = 'uniqueHangId' in config

    if config.searchRoot:
        submitter(config)
    else:
        try:
            with open(config.jsonfile) as jsonFile:
                formData = json.load(jsonFile)
            config.submissionFunc(formData,
                                  config.dumpfile,
                                  config.url)
        except Exception, x:
            sutil.reportExceptionAndContinue(config.logger)
