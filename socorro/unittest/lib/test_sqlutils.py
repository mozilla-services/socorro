# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_

from socorrolib.lib import sqlutils


def test_quote_value():
    eq_(sqlutils.quote_value('name'), "'name'")
    eq_(sqlutils.quote_value("'name'"), "'''name'''")
    eq_(sqlutils.quote_value("o'clock"), "'o''clock'")
