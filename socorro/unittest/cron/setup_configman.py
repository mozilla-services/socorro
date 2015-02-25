# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import Mock

from collections import Sequence

from socorro.cron.crontabber_app import CronTabber
from socorro.lib.util import SilentFakeLogger
from socorro.webapi.servers import WebServerBase

from configman import (
    Namespace,
    class_converter,
    ConfigurationManager,
    environment
)


#------------------------------------------------------------------------------
def get_standard_config_manager(
    more_definitions=None,
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
        overrides = [overrides].extend(local_overrides)
    else:
        overrides = local_overrides

    config_manager = ConfigurationManager(
        definitions,
        values_source_list=overrides,
        app_name='test-crontabber',
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
def get_config_manager_for_crontabber(
    more_definitions=None,
    jobs=None,
    overrides=None,
):
    if isinstance(more_definitions, Sequence):
        more_definitions = more_definitions.append(
            CronTabber.get_required_config()
        )
    elif more_definitions is not None:
        more_definitions = [
            more_definitions,
            CronTabber.get_required_config()
        ]
    else:
        more_definitions = [CronTabber.get_required_config()]

    local_overrides = {
        'logger': Mock(),
        #'resource.redactor.redactor_class': Mock(),
        'resource.postgresql.database_name': 'socorro_integration_test',
        'resource.postgresql.database_hostname': 'localhost',
        'secrets.postgresql.database_username': 'test',
        'secrets.postgresql.database_password': 'aPassword',
    }
    if jobs:
        local_overrides['crontabber.jobs'] = jobs

    if isinstance(overrides, Sequence):
        overrides.append(local_overrides)
    elif overrides is not None:
        overrides = [overrides, local_overrides]
    else:
        overrides = [local_overrides]

    return get_standard_config_manager(
        more_definitions=more_definitions,
        overrides=overrides
    )
