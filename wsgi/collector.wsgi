from socorro.app.generic_app import main
from socorro.collector.collector_app import CollectorApp
from socorro.webapi.servers import ApacheModWSGI
import socorro.collector.collector_app

from configman import ConfigFileFutureProxy

# invoke the generic main function to create the configman app class and which
# will then create the wsgi app object.
main(
  CollectorApp,  # the socorro app class
  config_path=ApacheModWSGI.get_socorro_config_path(__file__)
)

application = socorro.collector.collector_app.application

