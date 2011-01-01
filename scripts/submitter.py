#! /usr/bin/env python

import sys
import logging
import logging.handlers

import config.submitterconfig as subconf

import socorro.lib.ConfigurationManager as configurationManager
import socorro.collector.submitter as sub
import socorro.lib.util as sutil

try:
  config = configurationManager.newConfiguration(configurationModule=subconf,
                                                 applicationName="submitter 2.0")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("submitter")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

config.logger = logger

if config.numberOfSubmissions == 'forever':
    config.iteratorFunc = sub.createInfiniteFileSystemIterator
elif config.numberOfSubmissions == 'all':
    config.iteratorFunc = sub.createFileSystemIterator
else:
    config.iteratorFunc = sub.createLimitedFileSystemIterator
    config.numberOfSubmissions = int(config.numberOfSubmissions)

if config.dryrun:
    config.submissionFunc = sub.submissionDryRun
else:
    config.submissionFunc = sub.doSubmission

config.sleep = float(config.delay)/1000.0

config.uniqueHang = 'uniqueHangId' in config

if config.searchRoot:
    sub.submitter(config)
else:
    try:
        import json
        with open(config.jsonfile) as jsonFile:
            formData = json.load(jsonFile)
        config.submissionFunc(formData,
                              config.dumpfile,
                              config.url)
    except Exception, x:
        sutil.reportExceptionAndContinue(config.logger)
