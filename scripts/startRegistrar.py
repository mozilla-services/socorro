#!/usr/bin/python
import web
import datetime as dt
import itertools

import config.registrarconfig as configModule

import socorro.lib.ConfigurationManager as cm
import socorro.webapi.webapiService as webapi
import socorro.webapi.socorroweb as socweb
import socorro.webapi.classPartial as cpart
import socorro.registrar.registrar as sreg

import logging
import logging.handlers

try:
  configurationContext = cm.newConfiguration(configurationModule=configModule,
                               applicationName="Socorro Registrar 1.0")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()
logger = logging.getLogger("registrar")
logger.setLevel(logging.DEBUG)

stderrLog = logging.StreamHandler()
stderrLog.setLevel(configurationContext.stderrErrorLoggingLevel)
stderrLogFormatter = logging.Formatter(configurationContext.stderrLineFormatString)
stderrLog.setFormatter(stderrLogFormatter)
logger.addHandler(stderrLog)

syslog = logging.handlers.SysLogHandler(
  address=(configurationContext.syslogHost, configurationContext.syslogPort),
  facility=configurationContext.syslogFacilityString,
)
syslog.setLevel(configurationContext.syslogErrorLoggingLevel)
syslogFormatter = logging.Formatter(configurationContext.syslogLineFormatString)
syslog.setFormatter(syslogFormatter)
logger.addHandler(syslog)

logger.info("current configuration:")
for value in str(configurationContext).split('\n'):
  logger.info('%s', value)

configurationContext.logger = logger

web.webapi.internalerror = web.debugerror
web.config.debug = False

registrar = sreg.Registrar(configurationContext)

#-------------------------------------------------------------------------------
servicesList = (sreg.RegistrationService,
                sreg.DeregistrationService,
                sreg.TardyService,
                sreg.ProblemService,
                sreg.ListService,
                sreg.GetProcessorService,
                sreg.ProcessorForwardingService,
                sreg.RegistrarServicesQuery,
                sreg.ProcessorStatsService,
               )

registrar.services = servicesList

servicesUriTuples = ((x.uri,
                      cpart.classWithPartialInit(x, configurationContext, registrar))
                     for x in servicesList)
urls = tuple(itertools.chain(*servicesUriTuples))

logger.info(str(urls))

app =  socweb.SocorroWebApplication(configurationContext.serverIPAddress,
                                    configurationContext.serverPort,
                                    urls,
                                    globals())

if __name__ == "__main__":

  app.run()
