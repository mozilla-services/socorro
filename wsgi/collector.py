import os
from socorro.app.socorro_app import (
    SocorroWelcomeApp,
    main
)
from socorro.webapi.servers import WSGIServer
import socorro.collector.collector_app

from configman import (
    ConfigFileFutureProxy,
    environment
)

if os.path.isfile('/etc/socorro/collector.ini'):
    config_path = '/etc/socorro'
else:
    config_path = WSGIServer.get_socorro_config_path(__file__)

# invoke the generic main function to create the configman app class and which
# will then create the wsgi app object.
main(
    # we use the generic Socorro App class. We'll rely on configuration to set
    # the 'application' class object to the appropriate collector_app class
    # for example, it could be "CollectorApp"
    SocorroWelcomeApp,
    config_path=config_path,
    values_source_list=[
        ConfigFileFutureProxy,
        environment
    ]
)

application = socorro.collector.collector_app.application
