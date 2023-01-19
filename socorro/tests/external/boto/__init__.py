# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from configman import ConfigurationManager, environment


def get_config(cls, values_source=None):
    """Return config based on the required config of the cls.

    This uses environment configuration and configuration defaults
    and lets you override that by passing in a ``values_source``.

    :arg cls: a configman-enhanced class
    :arg values_source: dict of configurable overrides

    :returns: a configman config object

    """
    values_source = values_source or {}

    conf = cls.get_required_config()
    conf.add_option("logger", default=mock.Mock())
    conf.add_option("metrics", default=mock.Mock())

    cm = ConfigurationManager(
        [conf],
        app_name="testapp",
        app_version="1.0",
        app_description="",
        values_source_list=[environment, values_source],
        argv_source=[],
    )
    return cm.get_config()
