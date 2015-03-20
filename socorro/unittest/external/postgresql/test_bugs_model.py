# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_, assert_raises
from mock import Mock

from socorro.unittest.testbase import TestCase

from configman.dotdict import DotDict
from socorro.external.postgresql.bugs_model import Bugs, execute_query_fetchall


#==============================================================================
class TestBugsImpl(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = DotDict()
        config.logger = Mock()
        config.crashstorage_class = Mock()

        return config

    #--------------------------------------------------------------------------
    def test_instantiation(self):
        config = self.get_basic_config()
        expected_transaction_object = (
            config.crashstorage_class.return_value.transaction
        )

        # the call to be tested
        b = Bugs(config)

        eq_(b.config, config)
        eq_(b.transaction, expected_transaction_object)


    #--------------------------------------------------------------------------
    def test_signatures(self):
        config = self.get_basic_config()
        expected_transaction_object = (
            config.crashstorage_class.return_value.transaction
        )
        transaction_return_value = [
            ('sig1', '123456'),
            ('sig2', '123456'),
            ('sig3', '123456'),
        ]
        expected_transaction_object.return_value = transaction_return_value

        expected_result = [
            {'signature': 'sig1', 'id': '123456'},
            {'signature': 'sig2', 'id': '123456'},
            {'signature': 'sig3', 'id': '123456'},
        ]

        b = Bugs(config)

        # the call to be tested
        result = b.signatures('123456')
        eq_(result, expected_result)

    #--------------------------------------------------------------------------
    def test_bug_ids(self):
        config = self.get_basic_config()
        expected_transaction_object = (
            config.crashstorage_class.return_value.transaction
        )
        transaction_return_value = [
            ('sig1', '123456'),
            ('sig2', '123456'),
            ('sig3', '123456'),
        ]
        expected_transaction_object.return_value = transaction_return_value

        expected_result = [
            {'signature': 'sig1', 'id': '123456'},
            {'signature': 'sig2', 'id': '123456'},
            {'signature': 'sig3', 'id': '123456'},
        ]

        b = Bugs(config)

        # the call to be tested
        result = b.bug_ids('123456')
        eq_(result, expected_result)
