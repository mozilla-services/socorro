#!/usr/bin/python

import web
import itertools

import socorro.lib.ConfigurationManager as cm
import socorro.lib.util as sutil
import socorro.webapi.webapiService as webapi
import socorro.webapi.classPartial as cpart
import socorro.webapi.webapp as sweb
import socorro.services.hello as hello
import socorro.storage.hbaseClient as hbc

#===============================================================================
commandLineOptions = [
  ('h', 'host', True, '0.0.0.0', "Interface to listen on"),
  ('p', 'port', True, 9091, 'the port to listen to'),
  (None, 'thriftHost', True, 'localhost', "the thrift host"),
  (None, 'thriftPort', True, 9090, "the thrift port"),
  (None, 'thriftTimeout', True, 5000, "the thrift timeout"),
  (None, 'help', False, None, "print this"),
]
config =  cm.newConfiguration(configurationOptionsList=commandLineOptions,
                              applicationName="Thrift Health 1.0")
print "current configuration:"
config.output()
config.logger = sutil.SilentFakeLogger()
#===============================================================================
class ThriftHealthService(webapi.JsonServiceBase):
  #-----------------------------------------------------------------------------
  def __init__(self, context):
    super(ThriftHealthService, self).__init__(context)
  #-----------------------------------------------------------------------------
  uri = '/thrift/health'
  #-----------------------------------------------------------------------------
  def get(self, *args):
    try:
      conn = hbc.HBaseConnection(self.context.thriftHost,
                                 self.context.thriftPort,
                                 self.context.thriftTimeout)
      try:
        descriptors = conn.describe_table('.META.')
      finally:
        conn.close()
      return "success"
    except Exception:
      return "fail"


#===============================================================================
web.webapi.internalerror = web.debugerror
web.config.debug = False
servicesList = (ThriftHealthService,
                hello.Hello,
               )
servicesUriTuples = ((x.uri,
                      cpart.classWithPartialInit(x, config))
                     for x in servicesList)
urls = tuple(itertools.chain(*servicesUriTuples))
print "services: %s" % str(urls)
app =  sweb.StandAloneWebApplication(config.host,
                                     config.port,
                                     urls,
                                     globals())

#===============================================================================
if __name__ == "__main__":
    app.run()
