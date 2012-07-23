from socorro.app.generic_app import main
from socorro.collector.collector_app import CollectorApp
import socorro.collector.collector_app

from configman import ConfigFileFutureProxy

import os

# we need to set a custom path for configuration
def determine_socorro_config():
    wsgi_path = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(wsgi_path, '..', 'config')
    return os.path.abspath(config_path)

# invoke the generic main function to create the configman app class and which
# will then create the wsgi app object.
main(
  CollectorApp,  # the socorro app class
  config_path=determine_socorro_config()
)

application = socorro.collector.collector_app.application

