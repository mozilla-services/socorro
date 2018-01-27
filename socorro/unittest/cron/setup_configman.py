# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import Mock

from collections import Sequence

from socorro.cron.crontabber_app import CronTabberApp
from socorro.lib.util import SilentFakeLogger

from configman import (
    Namespace,
    ConfigurationManager,
    environment
)


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

    return config_manager


def get_config_manager_for_crontabber(
    more_definitions=None,
    jobs=None,
    overrides=None,
):
    if isinstance(more_definitions, Sequence):
        more_definitions = more_definitions.append(
            CronTabberApp.get_required_config()
        )
    elif more_definitions is not None:
        more_definitions = [
            more_definitions,
            CronTabberApp.get_required_config()
        ]
    else:
        more_definitions = [CronTabberApp.get_required_config()]

    local_overrides = {}
    if jobs:
        local_overrides['crontabber.jobs'] = jobs

    if isinstance(overrides, Sequence):
        overrides.append(local_overrides)
    elif overrides is not None:
        overrides = [overrides, local_overrides]
    else:
        overrides = [local_overrides]

    # Be sure to include defaults
    overrides.insert(0, CronTabberApp.config_module)

    return get_standard_config_manager(
        more_definitions=more_definitions,
        overrides=overrides
    )
