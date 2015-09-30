# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import Mock, patch
from nose.tools import eq_, ok_
from contextlib import contextmanager

from configman.dotdict import DotDict, DotDictWithAcquisition

from socorro.unittest.testbase import TestCase

from socorro.webapi.class_partial import class_with_partial_init


#==============================================================================
class TestPartialForServiceClasses(TestCase):

    #--------------------------------------------------------------------------
    def test_partial_1(self):

        local_config = DotDict()

        class A(object):

            def __init__(self, config):
                eq_(local_config, config)

        wrapped_class = class_with_partial_init(A, local_config)
        a = wrapped_class()
        eq_(wrapped_class.global_config, None)


    #--------------------------------------------------------------------------
    def test_partial_2(self):
        local_config = DotDict()
        global_config = DotDict()

        class A(object):

            def __init__(self, config):
                eq_(local_config, config)

        wrapped_class = class_with_partial_init(A, local_config, global_config)
        a = wrapped_class()
        eq_(wrapped_class.global_config, global_config)

    #--------------------------------------------------------------------------
    def test_partial_3(self):

        d = {
            'x': DotDictWithAcquisition()
        }
        d['x'].local_config = DotDictWithAcquisition()

        class A(object):

            def __init__(self, config):
                self.config = config
                eq_(d['x'].local_config, config)

        wrapped_class = class_with_partial_init(
            A,
            d['x'].local_config,
        )
        a = wrapped_class()
        del d['x']
        # the DotDictWithAcquisition should try to look to its parent
        # for the key "bad_key", but the weakly referenced parent should be
        # gone and raise a ReferenceError
        try:
            a.config.bad_key
        except ReferenceError:
            # this is the correct behavior
            # 'assertRaises' was not used because we're not testing a callable
            pass

    #--------------------------------------------------------------------------
    def test_partial_4(self):

        d = {
            'x': DotDictWithAcquisition()
        }
        d['x'].local_config = DotDictWithAcquisition()

        class A(object):

            def __init__(self, config):
                self.config = config
                eq_(d['x'].local_config, config)

        wrapped_class = class_with_partial_init(
            A,
            d['x'].local_config,
            d['x']
        )
        a = wrapped_class()
        del d['x']
        # the DotDictWithAcquisition should try to look to its parent
        # for the key "bad_key", but the weakly referenced parent should be
        # saved in the wrapped class.  That means the 'bad_key' should raise
        # a 'KeyError' instead
        try:
            a.config.bad_key
        except KeyError:
            # this is the correct behavior
            # 'assertRaises' was not used because we're not testing a callable
            pass
