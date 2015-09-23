# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import web
import os

from socorro.webapi.class_partial import class_with_partial_init

from configman import Namespace, RequiredConfig


#==============================================================================
class WebServerBase(RequiredConfig):
    required_config = Namespace()

    #--------------------------------------------------------------------------
    def __init__(self, config, services_list):
        self.config = config

        urls = []

        for each in services_list:

            if hasattr(each, 'uri'):
                # this service has a hard coded uri embedded within
                uri, cls = each.uri, each
                config.logger.debug(
                    'embedded uri class %s %s',
                    cls.__name__,
                    uri
                )
            else:
                # this is a uri, service pair
                uri, cls = each
                config.logger.debug(
                    'service pair uri class %s %s',
                    cls.__name__,
                    uri
                )

            if isinstance(uri, basestring):
                uri = (uri, )

            for a_uri in uri:
                urls.append(a_uri)
                if hasattr(cls, 'wrapped_partial'):
                    config.logger.debug(
                        "appending already wrapped %s",
                        cls.__name__
                    )
                    urls.append(cls)
                else:
                    config.logger.debug(
                        "wrapping %s",
                        cls.__name__
                    )
                    urls.append(class_with_partial_init(cls, config))

        self.urls = tuple(urls)

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
class WSGIServer(WebServerBase):
    """When running under a wsgi compatible Web server, modwsgi requires a
    reference to a "wsgifunc" In this varient of the WebServer class, the run
    function returns the result of the webpy framework's wsgifunc.
    Applications that use this class must provide a module level variable
    'application' in the module given to the Web server modwsgi configuration.
    The value of the variable must be the _wsgi_func.
    """

    #--------------------------------------------------------------------------
    def run(self):
        return self._wsgi_func

    #--------------------------------------------------------------------------
    def _identify(self):
        self.config.logger.info('this is WSGIServer')

    #--------------------------------------------------------------------------
    @staticmethod
    def get_socorro_config_path(wsgi_file):
        wsgi_path = os.path.dirname(os.path.realpath(wsgi_file))
        config_path = os.path.join(wsgi_path, '..', 'config')
        return os.path.abspath(config_path)

ApacheModWSGI = WSGIServer  # for backwards compatiblity


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
