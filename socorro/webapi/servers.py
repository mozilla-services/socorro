# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import web
import os

from socorro.webapi.classPartial import classWithPartialInit

from configman import Namespace, RequiredConfig


#==============================================================================
class WebServerBase(RequiredConfig):
    required_config = Namespace()

    #--------------------------------------------------------------------------
    def __init__(self, config, services_list):
        self.config = config
        self.urls = tuple(y for a_tuple in
                         ((uri, classWithPartialInit(x, config))
                            for uri, x in services_list) for y in a_tuple)
        #self.config.logger.info(str(self.urls))
        web.webapi.internalerror = web.debugerror
        web.config.debug = False
        self._identify()
        self._wsgi_func = web.application(self.urls, globals()).wsgifunc()

    #--------------------------------------------------------------------------
    def run(self):
        raise NotImplemented

    #--------------------------------------------------------------------------
    def _identify(self):
        pass


#==============================================================================
class ApacheModWSGI(WebServerBase):
    """When running Apache, modwsgi requires a reference to a "wsgifunc" In
    this varient of the WebServer class, the run function returns the result of
    the webpy framework's wsgifunc.  Applications that use this class must
    provide a module level variable 'application' in the module given to Apache
    modwsgi configuration.  The value of the variable must be the _wsgi_func.
    """

    #--------------------------------------------------------------------------
    def run(self):
        return self._wsgi_func

    #--------------------------------------------------------------------------
    def _identify(self):
        self.config.logger.info('this is ApacheModWSGI')

    #--------------------------------------------------------------------------
    @staticmethod
    def get_socorro_config_path(wsgi_file):
        wsgi_path = os.path.dirname(os.path.realpath(wsgi_file))
        config_path = os.path.join(wsgi_path, '..', 'config')
        return os.path.abspath(config_path)


#==============================================================================
class StandAloneServer(WebServerBase):
    required_config = Namespace()
    required_config.add_option(
      'port',
      doc='the port to listen to for submissions',
      default=8882
    )


#==============================================================================
class CherryPy(StandAloneServer):
    required_config = Namespace()
    required_config.add_option(
      'ip_address',
      doc='the IP address from which to accept submissions',
      default='127.0.0.1'
    )

    #--------------------------------------------------------------------------
    def run(self):
        web.runsimple(
          self._wsgi_func,
          (self.config.web_server.ip_address, self.config.web_server.port)
        )

    #--------------------------------------------------------------------------
    def _identify(self):
        self.config.logger.info(
          'this is CherryPy from web.py running standalone at %s:%d',
          self.config.web_server.ip_address,
          self.config.web_server.port
        )
