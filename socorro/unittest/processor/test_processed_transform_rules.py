# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_, ok_

from socorro.lib.util import DotDict, SilentFakeLogger, FakeLogger
from socorro.processor.processed_transform_rules import (
    OOMSignature,
    SigTrunc,
)

from socorro.processor.signature_utilities import CSignatureTool
from socorro.unittest.testbase import TestCase

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
    #fake_processor.config.logger = SilentFakeLogger()
    fake_processor.config.logger = FakeLogger()
    return fake_processor


class TestOOMSignature(TestCase):

    def test_OOMAllocationSize_predicate_no_match(self):
        pc = DotDict()
        pc.signature = 'hello'
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(not predicate_result)

    def test_OOMAllocationSize_predicate(self):
        pc = DotDict()
        pc.signature = 'hello'
        rd = {}
        rc = DotDict()
        rc.OOMAllocationSize = 17
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(predicate_result)

    def test_OOMAllocationSize_predicate_signature_fragment_1(self):
        pc = DotDict()
        pc.signature = 'this | is | a | NS_ABORT_OOM | signature'
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(predicate_result)

    def test_OOMAllocationSize_predicate_signature_fragment_2(self):
        pc = DotDict()
        pc.signature = 'mozalloc_handle_oom | this | is | bad'
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(predicate_result)

    def test_OOMAllocationSize_predicate_signature_fragment_3(self):
        pc = DotDict()
        pc.signature = 'CrashAtUnhandlableOOM'
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(predicate_result)

    def test_OOMAllocationSize_action_success(self):
        pc = DotDict()
        pc.signature = 'hello'

        fake_processor = create_basic_fake_processor()

        rc = DotDict()
        rd = {}

        rule = OOMSignature(fake_processor.config)
        action_result = rule.action(rc, rd, pc, fake_processor)

        ok_(action_result)
        ok_(pc.original_signature, 'hello')
        ok_(pc.signature, 'OOM | unknown | hello')

    def test_OOMAllocationSize_action_small(self):
        pc = DotDict()
        pc.signature = 'hello'

        fake_processor = create_basic_fake_processor()

        rc = DotDict()
        rc.OOMAllocationSize = 17
        rd = {}

        rule = OOMSignature(fake_processor.config)
        action_result = rule.action(rc, rd, pc, fake_processor)

        ok_(action_result)
        ok_(pc.original_signature, 'hello')
        ok_(pc.signature, 'OOM | small')

    def test_OOMAllocationSize_action_large(self):
        pc = DotDict()
        pc.signature = 'hello'

        fake_processor = create_basic_fake_processor()

        rc = DotDict()
        rc.OOMAllocationSize = 17000000
        rd = {}

        rule = OOMSignature(fake_processor.config)
        action_result = rule.action(rc, rd, pc, fake_processor)

        ok_(action_result)
        ok_(pc.original_signature, 'hello')
        ok_(pc.signature, 'OOM | large | hello')

    def test_SigTrunc_predicate_no_match(self):
        pc = DotDict()
        pc.signature = '0' * 100
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = SigTrunc(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(not predicate_result)

    def test_SigTrunc_predicate(self):
        pc = DotDict()
        pc.signature = '9' * 256
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = SigTrunc(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(predicate_result)

    def test_SigTrunc_action_success(self):
        pc = DotDict()
        pc.signature = '9' * 256
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = SigTrunc(fake_processor.config)
        predicate_result = rule.action(rc, rd, pc, fake_processor)
        ok_(predicate_result)
        eq_(len(pc.signature), 255)
        ok_(pc.signature.endswith('9...'))
