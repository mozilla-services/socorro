# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os

import pytest


@pytest.fixture
def capabilities(request, capabilities):
    driver = request.config.getoption('driver')
    if capabilities.get('browserName', driver).lower() == 'firefox':
        capabilities['marionette'] = True
    return capabilities


@pytest.fixture(scope='session')
def session_capabilities(pytestconfig, session_capabilities):
    if pytestconfig.getoption('driver') == 'SauceLabs':
        session_capabilities.setdefault('tags', []).append('socorro')
    return session_capabilities


@pytest.fixture
def firefox_options(firefox_options):
    if os.environ.get('MOZ_HEADLESS') == '1':
        firefox_options.binary = os.environ.get('MOZ_BINARY_PATH')

    return firefox_options
