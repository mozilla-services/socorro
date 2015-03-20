# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import Mock

from collections import Sequence

from socorro.dataservice.dataservice_app import DataserviceApp
from socorro.lib.util import SilentFakeLogger
from socorro.webapi.servers import WebServerBase

from configman import (
    Namespace,
    class_converter,
    ConfigurationManager,
    environment
)


#==============================================================================
class MyWSGIServer(WebServerBase):

    def run(self):
        return self


#------------------------------------------------------------------------------
def get_standard_config_manager(
    more_definitions=None,
    service_classes=None,
    overrides=None,
):
    # MOCKED CONFIG DONE HERE
    required_config = Namespace()
    required_config.add_option(
        'logger',
        default=SilentFakeLogger(),
        doc='a logger',
    )
    required_config.add_option(
        'executor_identity',
        default=Mock()
    )
    if service_classes:
        required_config.namespace('services')
        if not isinstance(service_classes, Sequence):
            service_classes = (service_classes,)
        for service_class in service_classes:
            # config for the services being tested
            service_name = service_class.__name__.split('.')[-1]
            required_config.services.namespace(service_name)
            # adding the service as if it had been put in via the
            # classes_in_namespaces converter defined in the dataservice
            # package.  Configman will pull the services additional
            # requirements
            required_config.services[service_name].add_option(
                'cls',
                default=service_class,
                from_string_converter=class_converter
            )

    if isinstance(more_definitions, Sequence):
        definitions = [required_config]
        definitions.extend(more_definitions)
    elif more_definitions is not None:
        definitions = [required_config, more_definitions]
    else:
        definitions = [required_config]

    local_overrides = [
        environment,
    ]

    if isinstance(overrides, Sequence):
        overrides.extend(local_overrides)
    elif overrides is not None:
        overrides = [overrides] + local_overrides
    else:
        overrides = local_overrides

    config_manager = ConfigurationManager(
        definitions,
        values_source_list=overrides,
        app_name='ES tests',
        app_description=__doc__,
        argv_source=[]
    )

    # very useful debug
    #import contextlib
    #import sys
    #@contextlib.contextmanager
    #def stdout_opener():
        #yield sys.stdout
    #config_manager.write_conf('conf', stdout_opener)

    return config_manager


#------------------------------------------------------------------------------
def get_config_manager_with_internal_pg(
    more_definitions=None,
    service_classes=None,
    overrides=None,
):
    internal_namespace = Namespace()
    internal_namespace.namespace('database')
    internal_namespace.database.add_option(
        'crashstorage_class',
        default='socorro'
                '.external.postgresql.crashstorage.PostgreSQLCrashStorage',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql'
    )
    internal_namespace.database.add_option(
        name='database_superusername',
        default='test',
        doc='Username to connect to database',
    )
    internal_namespace.database.add_option(
        name='database_superuserpassword',
        default='aPassword',
        doc='Password to connect to database',
    )
    if isinstance(more_definitions, Sequence):
        more_definitions.append(internal_namespace)
    elif more_definitions is not None:
        more_definitions = [more_definitions, internal_namespace]
    else:
        more_definitions = [internal_namespace]

    return get_standard_config_manager(
        more_definitions=more_definitions,
        service_classes=service_classes,
        overrides=overrides
    )


#------------------------------------------------------------------------------
def get_config_manager_for_dataservice(
    more_definitions=None,
    service_classes=None,
    overrides=None,
):
    if isinstance(more_definitions, Sequence):
        more_definitions = more_definitions.append(
            DataserviceApp.get_required_config()
        )
    elif more_definitions is not None:
        more_definitions = [
            more_definitions,
            DataserviceApp.get_required_config()
        ]
    else:
        more_definitions = [DataserviceApp.get_required_config()]

    local_overrides = {
        'logger': Mock(),
        'web_server.wsgi_server_class': MyWSGIServer
    }

    if isinstance(overrides, Sequence):
        overrides.append(local_overrides)
    elif overrides is not None:
        overrides = [overrides, local_overrides]
    else:
        overrides = [local_overrides]

    return get_config_manager_with_internal_pg(
        more_definitions=more_definitions,
        service_classes=service_classes,
        overrides=overrides
    )
