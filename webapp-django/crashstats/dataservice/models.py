# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf import settings
from configman import (
    configuration,
    # ConfigFileFutureProxy,
    Namespace,
    environment
)
from socorro.app.socorro_app import App

from socorro.dataservice.util import (
    classes_in_namespaces_converter,
)

SERVICES_LIST = ('socorro.external.postgresql.bugs_service.Bugs',)

# Allow configman to dynamically load the configuration and classes
# for our API dataservice objects
def_source = Namespace()
def_source.namespace('services')
def_source.services.add_option(
    'service_list',
    default=','.join(SERVICES_LIST),
    from_string_converter=classes_in_namespaces_converter()
)

settings.DATASERVICE_CONFIG = configuration(
    definition_source=[
        def_source,
        App.get_required_config(),
    ],
    values_source_list=[
        settings.DATASERVICE_CONFIG_BASE,
        # ConfigFileFutureProxy,
        environment
    ]
)
