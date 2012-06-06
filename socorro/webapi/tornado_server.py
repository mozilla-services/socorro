from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

from socorro.webapi.servers import StandAloneServer
from configman import Namespace

#==============================================================================
class Tornado(StandAloneServer):
    #--------------------------------------------------------------------------
    def run(self):
        container = WSGIContainer(self._wsgi_func)
        http_server = HTTPServer(container)
        http_server.listen(self.config.web_server.port)
        IOLoop.instance().start()

    #--------------------------------------------------------------------------
    def _identify(self):
        self.config.logger.info(
          'this is the Tornado Web Server on port: %d',
          self.config.web_server.port
        )

