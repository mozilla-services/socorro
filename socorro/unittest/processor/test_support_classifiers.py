# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import copy

from socorro.lib.util import DotDict, SilentFakeLogger
from socorro.processor.support_classifiers import (
    SupportClassificationRule,
    BitguardClassifier,
)

from socorro.processor.signature_utilities import CSignatureTool
from socorro.unittest.processor.test_breakpad_pipe_to_json import (
    cannonical_json_dump,
)

csig_config = DotDict()
csig_config.irrelevant_signature_re = ''
csig_config.prefix_signature_re = ''
csig_config.signatures_with_line_numbers_re = ''
csig_config.signature_sentinels = []
c_signature_tool = CSignatureTool(csig_config)


def create_basic_fake_processor():
    fake_processor = DotDict()
    fake_processor.c_signature_tool = c_signature_tool
    fake_processor.config = DotDict()
    # need help figuring out failures? switch to FakeLogger and read stdout
    fake_processor.config.logger = SilentFakeLogger()
    #fake_processor.config.logger = FakeLogger()
    return fake_processor


class TestSupportClassificationRule(unittest.TestCase):

    def test_predicate(self):
        rc = DotDict()
        pc = DotDict()
        pc.classifications = DotDict()
        processor = None

        support_rule = SupportClassificationRule()
        self.assertTrue(support_rule.predicate(rc, pc, processor))

        pc.classifications.support = DotDict()
        self.assertTrue(support_rule.predicate(rc, pc, processor))

    def test_action(self):
        rc = DotDict()
        pc = DotDict()
        processor = None

        support_rule = SupportClassificationRule()
        self.assertTrue(support_rule.action(rc, pc, processor))

    def test_version(self):
        support_rule = SupportClassificationRule()
        self.assertEqual(support_rule.version(), '0.0')

    def test_add_classification_to_processed_crash(self):
        pc = DotDict()
        pc.classifications = DotDict()

        support_rule = SupportClassificationRule()
        support_rule._add_classification(
            pc,
            'stupid',
            'extra stuff'
        )
        self.assertTrue('classifications' in pc)
        self.assertTrue('support' in pc.classifications)
        self.assertEqual(
            'stupid',
            pc.classifications.support.classification
        )
        self.assertEqual(
            'extra stuff',
            pc.classifications.support.classification_data
        )
        self.assertEqual(
            '0.0',
            pc.classifications.support.classification_version
        )


class TestBitguardClassfier(unittest.TestCase):

    def test_action_success(self):
        jd = copy.deepcopy(cannonical_json_dump)
        jd['modules'].append({'filename': 'bitguard.dll'})
        pc = DotDict()
        pc.json_dump = jd

        fake_processor = create_basic_fake_processor()

        rc = DotDict()

        rule = BitguardClassifier()
        action_result = rule.action(rc, pc, fake_processor)

        self.assertTrue(action_result)
        self.assertTrue('classifications' in pc)
        self.assertTrue('support' in pc.classifications)
        self.assertEqual(
            'bitguard',
            pc.classifications.support.classification
        )

    def test_action_fail(self):
        jd = copy.deepcopy(cannonical_json_dump)
        pc = DotDict()
        pc.json_dump = jd

        fake_processor = create_basic_fake_processor()

        rc = DotDict()

        rule = BitguardClassifier()
        action_result = rule.action(rc, pc, fake_processor)

        self.assertFalse(action_result)
        self.assertTrue('classifications' not in pc)

