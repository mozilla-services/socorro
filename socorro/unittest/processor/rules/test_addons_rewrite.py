# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
from nose.tools import eq_, ok_

from socorro.processor.rules.addons_rewrite import (
    AddonsRewriteRule,
)
from socorro.unittest.testbase import TestCase
from socorro.unittest.processor.test_signature_utilities import (
    create_basic_fake_processor
)


HERE = os.path.dirname(__file__)


class TestAddonsRewriteRule(TestCase):
    def get_config(self):
        fake_processor = create_basic_fake_processor()
        return fake_processor.config

    def test_predicate_success(self):
        config = self.get_config()
        rule = AddonsRewriteRule(config)

        processed_crash = {}
        processed_crash['addons'] = [['abcd', '1']]

        predicate_result = rule.predicate({}, {}, processed_crash, {})
        ok_(predicate_result)

    def test_predicate_no_match(self):
        config = self.get_config()
        rule = AddonsRewriteRule(config)

        processed_crash = {}

        predicate_result = rule.predicate({}, {}, processed_crash, {})
        ok_(not predicate_result)

        processed_crash['addons'] = []
        predicate_result = rule.predicate({}, {}, processed_crash, {})
        ok_(not predicate_result)

        processed_crash['addons'] = None
        predicate_result = rule.predicate({}, {}, processed_crash, {})
        ok_(not predicate_result)

        processed_crash['addons'] = ''
        predicate_result = rule.predicate({}, {}, processed_crash, {})
        ok_(not predicate_result)

    def test_action_success(self):
        config = self.get_config()
        rule = AddonsRewriteRule(config)

        processed_crash = {}
        processed_crash['addons'] = [
            ['abcd', '1'],
            ['efgh', 32],
        ]

        action_result = rule.action({}, {}, processed_crash, {})
        ok_(action_result)
        ok_('addons' in processed_crash)

        expected_res = [
            'abcd:1',
            'efgh:32',
        ]
        eq_(processed_crash['addons'], expected_res)

    def test_action_success_with_odd_number_of_addons(self):
        config = self.get_config()
        rule = AddonsRewriteRule(config)

        processed_crash = {}
        processed_crash['addons'] = [
            ['abcd', '1'],
            ['xyz'],  # note the lonely id here
            ['efgh', 32],
        ]

        action_result = rule.action({}, {}, processed_crash, {})
        ok_(action_result)
        ok_('addons' in processed_crash)

        expected_res = [
            'abcd:1',
            'xyz',
            'efgh:32',
        ]
        eq_(processed_crash['addons'], expected_res)
