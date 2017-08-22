#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import sys
import logging
import logging.handlers

import config.submitterconfig as subconf

import socorro.lib.ConfigurationManager as configurationManager
import socorro.submitter.submitter as sub
import socorro.lib.util as sutil

import poster

poster.streaminghttp.register_openers()

try:
  config = configurationManager.newConfiguration(configurationModule=subconf,
                                                 applicationName="submitter 2.0")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("submitter")
logger.setLevel(logging.DEBUG)

sutil.setup_logging_handlers(logger, config)
sutil.echo_config(logger, config)

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
                              config.url,
                              config.logger)
    except Exception, x:
        sutil.report_exception_and_continue(config.logger)
