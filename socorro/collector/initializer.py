# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import logging
import logging.handlers

import socorro.lib.ConfigurationManager
import socorro.lib.util as sutil
import socorro.lib.JsonDumpStorage as jds

import socorro.storage.crashstorage as cstore


#-----------------------------------------------------------------------------------------------------------------
def createPersistentInitialization(configModule):
  storage = sutil.DotDict()

  storage.config = config = socorro.lib.ConfigurationManager.newConfiguration(configurationModule=configModule,automaticHelp=False)
  storage.logger = logger = logging.getLogger("collector")

  logger.setLevel(logging.DEBUG)

  address = None
  if config.syslogTransport == 'socket':
    address = config.syslogSocket
  elif config.syslogTransport == 'udp':
    address = (config.syslogHost, config.syslogPort)
  else:
    from socorro.lib.ConfigurationManager import OptionError
    raise OptionError('Unknown syslog transport %s') % config.syslogTransport

  syslog = logging.handlers.SysLogHandler(
    address=address,
    facility=config.syslogFacilityString,
  )
  syslog.setLevel(config.syslogErrorLoggingLevel)
  syslogFormatter = logging.Formatter(config.syslogLineFormatString)
  syslog.setFormatter(syslogFormatter)
  logger.addHandler(syslog)

  logger.info("current configuration:")
  for value in str(config).split('\n'):
      logger.info('%s', value)

  storage.config['logger'] = logger

  storage.crashStorage = config.primaryStorageClass(config)

  storage.legacyThrottler = cstore.LegacyThrottler(config)

  return storage
