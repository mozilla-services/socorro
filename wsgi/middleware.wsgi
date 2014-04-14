import os
from socorro.app.generic_app import main
from socorro.middleware.middleware_app import MiddlewareApp
from socorro.webapi.servers import ApacheModWSGI
import socorro.middleware.middleware_app

if os.path.isfile('/etc/socorro/middleware.ini'):
    config_path = '/etc/socorro'
else:
    config_path = ApacheModWSGI.get_socorro_config_path(__file__)

# invoke the generic main function to create the configman app class and which
# will then create the wsgi app object.
main(
    MiddlewareApp,  # the socorro app class
    config_path=config_path
)

application = socorro.middleware.middleware_app.application
