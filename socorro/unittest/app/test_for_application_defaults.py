# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_, ok_

from configman.dotdict import DotDict

from socorro.unittest.testbase import TestCase
from socorro.app.for_application_defaults import (
    ApplicationDefaultsProxy,
    ValueSource,
)
from socorro.app.socorro_app import App


# for use in a later test
class SomeApp(App):
    @classmethod
    def get_application_defaults(klass):
        defaults = DotDict()
        defaults.alpha = 17
        defaults.beta = 23
        return defaults


class TestApplicationDefaultsProxy(TestCase):

    def setUp(self):
        self.proxy = ApplicationDefaultsProxy()

    def test_application_defaults(self):
        new_proxy = ApplicationDefaultsProxy()
        eq_(new_proxy.application_defaults, DotDict())

        new_proxy.str_to_application_class(
            'socorro.unittest.app.test_for_application_defaults.SomeApp'
        )

        eq_(
            dict(new_proxy.application_defaults),
            {
                'alpha': 17,
                'beta': 23,
            }
        )


class TestValueSource(TestCase):

    def test_get_values(self):
        new_proxy = ApplicationDefaultsProxy()
        vs = ValueSource(new_proxy)
        eq_(
            vs.get_values(None, None, dict),
            {}
        )
        eq_(
            vs.get_values(None, None, DotDict),
            DotDict()
        )
        new_proxy.str_to_application_class(
            'socorro.unittest.app.test_for_application_defaults.SomeApp'
        )
        eq_(
            vs.get_values(None, None, dict),
            {
                'alpha': 17,
                'beta': 23,
            }
        )
        ok_(isinstance(vs.get_values(None, None, DotDict), DotDict))
