import os
from socorro.app.socorro_app import main
from socorro.middleware.middleware_app import MiddlewareApp
from socorro.webapi.servers import WSGIServer
import socorro.middleware.middleware_app

from configman import (
    ConfigFileFutureProxy,
    environment
)

if os.path.isfile('/etc/socorro/middleware.ini'):
    config_path = '/etc/socorro'
else:
    config_path = WSGIServer.get_socorro_config_path(__file__)

# invoke the socorro main function to create the configman app class and which
# will then create the wsgi app object.
main(
    MiddlewareApp,  # the socorro app class
    config_path=config_path,
    values_source_list=[
        ConfigFileFutureProxy,
        environment
    ]
)

application = socorro.middleware.middleware_app.application
