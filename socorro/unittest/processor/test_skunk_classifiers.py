# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy

from socorro.lib.util import DotDict
from socorro.processor.skunk_classifiers import (
    SkunkClassificationRule,
    DontConsiderTheseFilter,
    SetWindowPos,
)
from socorro.unittest.processor import (
    create_basic_fake_processor,
    c_signature_tool,
)
from socorro.unittest.processor.test_breakpad_pipe_to_json import (
    cannonical_json_dump
)
from socorro.unittest.testbase import TestCase


class TestSkunkClassificationRule(TestCase):

    def test_predicate(self):
        rc = DotDict()
        rd = {}
        pc = DotDict()
        pc.classifications = DotDict()
        processor = None

        skunk_rule = SkunkClassificationRule()
        assert skunk_rule.predicate(rc, rd, pc, processor)

        pc.classifications.skunk_works = DotDict()
        assert skunk_rule.predicate(rc, rd, pc, processor)

        pc.classifications.skunk_works.classification = 'stupid'
        assert not skunk_rule.predicate(rc, rd, pc, processor)

    def test_action(self):
        rc = DotDict()
        rd = {}
        pc = DotDict()
        processor = None

        skunk_rule = SkunkClassificationRule()
        assert skunk_rule.action(rc, rd, pc, processor)

    def test_version(self):
        skunk_rule = SkunkClassificationRule()
        assert skunk_rule.version() == '0.0'

    def test_add_classification_to_processed_crash(self):
        pc = DotDict()
        pc.classifications = DotDict()

        skunk_rule = SkunkClassificationRule()
        skunk_rule._add_classification(
            pc,
            'stupid',
            'extra stuff'
        )
        assert 'classifications' in pc
        assert 'skunk_works' in pc.classifications
        assert 'stupid' == pc.classifications.skunk_works.classification
        assert 'extra stuff' == pc.classifications.skunk_works.classification_data
        assert '0.0' == pc.classifications.skunk_works.classification_version

    def test_get_stack(self):
        pc = DotDict()
        pc.process_type = 'plugin'
        skunk_rule = SkunkClassificationRule()

        assert not skunk_rule._get_stack(pc, 'upload_file_minidump_plugin')

        pc.json_dump = DotDict()
        pc.json_dump.threads = []
        assert not skunk_rule._get_stack(pc, 'upload_file_minidump_plugin')

        pc.json_dump.crash_info = DotDict()
        pc.json_dump.crash_info.crashing_thread = 1
        assert not skunk_rule._get_stack(pc, 'upload_file_minidump_plugin')

        pc.json_dump = cannonical_json_dump
        expected = cannonical_json_dump['crashing_thread']['frames']
        assert skunk_rule._get_stack(pc, 'upload_file_minidump_plugin') == expected

    def test_stack_contains(self):
        stack = cannonical_json_dump['threads'][1]['frames']

        skunk_rule = SkunkClassificationRule()
        assert skunk_rule._stack_contains(
            stack,
            'ha_',
            c_signature_tool,
            cache_normalizations=False
        )
        assert not skunk_rule._stack_contains(
            stack,
            'heh_',
            c_signature_tool,
            cache_normalizations=False
        )
        assert 'normalized' not in stack[0]
        assert skunk_rule._stack_contains(
            stack,
            'ha_ha2',
            c_signature_tool,
        )
        assert 'normalized' in stack[0]


class TestDontConsiderTheseFilter(TestCase):

    def test_action_predicate_accept(self):
        """test all of the case where the predicate should return True"""
        filter_rule = DontConsiderTheseFilter()

        fake_processor = create_basic_fake_processor()

        # find non-plugin crashes
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '0'
        test_raw_dumps = {}
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            DotDict(),
            fake_processor
        )

        # find non-Firefox crashes
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Internet Explorer"
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            DotDict(),
            fake_processor
        )

        # find crashes with no Version info
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            DotDict(),
            fake_processor
        )

        # find crashes with faulty Version info
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = 'dwight'
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            DotDict(),
            fake_processor
        )

        # find crashes with no BuildID info
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '17.1'
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            DotDict(),
            fake_processor
        )

        # find crashes with faulty BuildID info
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '17.1'
        test_raw_crash.BuildID = '201307E2'
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            DotDict(),
            fake_processor
        )

        # find crashes with faulty BuildID info (not integer)
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '17.1'
        test_raw_crash.BuildID = '201307E2'
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            DotDict(),
            fake_processor
        )

        # find crashes with faulty BuildID info (bad month & day)
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '17.1'
        test_raw_crash.BuildID = '20131458'
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            DotDict(),
            fake_processor
        )

        # find crashes with pre-17 version
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '15'
        test_raw_crash.BuildID = '20121015'
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            DotDict(),
            fake_processor
        )

        # find crashes with 18 version but build date less than 2012-10-23
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '18'
        test_raw_crash.BuildID = '20121015'
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            DotDict(),
            fake_processor
        )

        # find crashes with build date less than 2012-10-17
        # and version 17 or above
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '17'
        test_raw_crash.BuildID = '20121015'
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            DotDict(),
            fake_processor
        )

        # find crashes with no default dump
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '19'
        test_raw_crash.BuildID = '20121031'
        test_processed_crash = DotDict()
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            test_processed_crash,
            fake_processor
        )

        # find crashes with no architecture info
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '19'
        test_raw_crash.BuildID = '20121031'
        test_processed_crash = DotDict()
        test_processed_crash.dump = 'fake dump'
        test_processed_crash.json_dump = DotDict()
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            test_processed_crash,
            fake_processor
        )

        # find crashes with amd64 architecture info
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '19'
        test_raw_crash.BuildID = '20121031'
        test_processed_crash = DotDict()
        test_processed_crash.dump = 'fake dump'
        test_processed_crash.json_dump = DotDict()
        test_processed_crash.json_dump.system_info = DotDict()
        test_processed_crash.json_dump.cpu_arch = 'amd64'
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            test_processed_crash,
            fake_processor
        )

        # find crashes with main dump processing errors
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '19'
        test_raw_crash.BuildID = '20121031'
        test_processed_crash = DotDict()
        test_processed_crash.dump = 'fake dump'
        test_processed_crash.json_dump = DotDict()
        test_processed_crash.json_dump.system_info = DotDict()
        test_processed_crash.json_dump.system_info.cpu_arch = 'x86'
        test_processed_crash.success = False
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            test_processed_crash,
            fake_processor
        )

        # find crashes with extra dump processing errors
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '19'
        test_raw_crash.BuildID = '20121031'
        test_processed_crash = DotDict()
        test_processed_crash.dump = 'fake dump'
        test_processed_crash.json_dump = DotDict()
        test_processed_crash.json_dump.system_info = DotDict()
        test_processed_crash.json_dump.system_info.cpu_arch = 'x86'
        test_processed_crash.success = True
        test_processed_crash.additional_minidumps = ['a', 'b', 'c']
        test_processed_crash.a = DotDict()
        test_processed_crash.a.success = True
        test_processed_crash.b = DotDict()
        test_processed_crash.b.success = True
        test_processed_crash.c = DotDict()
        test_processed_crash.c.success = False
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            test_processed_crash,
            fake_processor
        )

        # find crashes with missing critical attribute
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '19'
        test_raw_crash.BuildID = '20121031'
        test_processed_crash = DotDict()
        test_processed_crash.dump = 'fake dump'
        test_processed_crash.json_dump = DotDict()
        test_processed_crash.json_dump.system_info = DotDict()
        test_processed_crash.json_dump.system_info.cpu_arch = 'x86'
        test_processed_crash.success = True
        test_processed_crash.additional_minidumps = ['a', 'b', 'c']
        test_processed_crash.a = DotDict()
        test_processed_crash.a.success = True
        test_processed_crash.b = DotDict()
        test_processed_crash.b.success = True
        test_processed_crash.c = DotDict()
        test_processed_crash.c.success = False
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            test_processed_crash,
            fake_processor
        )

        # find crashes with missing critical attribute
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '19'
        test_raw_crash.BuildID = '20121031'
        test_processed_crash = DotDict()
        test_processed_crash.dump = 'fake dump'
        test_processed_crash.json_dump = DotDict()
        test_processed_crash.json_dump.system_info = DotDict()
        test_processed_crash.json_dump.system_info.cpu_arch = 'x86'
        test_processed_crash.success = True
        test_processed_crash.additional_minidumps = ['a', 'b', 'c']
        test_processed_crash.a = DotDict()
        test_processed_crash.a.success = True
        test_processed_crash.b = DotDict()
        test_processed_crash.b.success = True
        test_processed_crash.c = DotDict()
        test_processed_crash.c.success = False
        assert filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            test_processed_crash,
            fake_processor
        )

        # reject the perfect crash
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '19'
        test_raw_crash.BuildID = '20121031'
        test_processed_crash = DotDict()
        test_processed_crash.dump = 'fake dump'
        test_processed_crash.json_dump = DotDict()
        test_processed_crash.json_dump.system_info = DotDict()
        test_processed_crash.json_dump.system_info.cpu_arch = 'x86'
        test_processed_crash.success = True
        test_processed_crash.additional_minidumps = ['a', 'b', 'c']
        test_processed_crash.a = DotDict()
        test_processed_crash.a.success = True
        test_processed_crash.b = DotDict()
        test_processed_crash.b.success = True
        test_processed_crash.c = DotDict()
        test_processed_crash.c.success = True
        assert not filter_rule.predicate(
            test_raw_crash,
            test_raw_dumps,
            test_processed_crash,
            fake_processor
        )

        # test the do-nothing action
        test_raw_crash = DotDict()
        test_raw_crash.PluginHang = '1'
        test_raw_crash.ProductName = "Firefox"
        test_raw_crash.Version = '19'
        test_raw_crash.BuildID = '20121031'
        test_processed_crash = DotDict()
        test_processed_crash.dump = 'fake dump'
        test_processed_crash.json_dump = DotDict()
        test_processed_crash.json_dump.system_info = DotDict()
        test_processed_crash.json_dump.system_info.cpu_arch = 'x86'
        test_processed_crash.success = True
        test_processed_crash.additional_minidumps = ['a', 'b', 'c']
        test_processed_crash.a = DotDict()
        test_processed_crash.a.success = True
        test_processed_crash.b = DotDict()
        test_processed_crash.b.success = True
        test_processed_crash.c = DotDict()
        test_processed_crash.c.success = True
        assert filter_rule.action(
            test_raw_crash,
            test_raw_dumps,
            test_processed_crash,
            fake_processor
        )


class TestSetWindowPos(TestCase):

    def test_action_case_1(self):
        """sentinel exsits in stack, but no secondaries"""
        pc = DotDict()
        pc.process_type = 'plugin'
        pijd = copy.deepcopy(cannonical_json_dump)
        pc.json_dump = pijd
        pc.json_dump['crashing_thread']['frames'][2]['function'] = \
            'NtUserSetWindowPos'
        f2jd = copy.deepcopy(cannonical_json_dump)
        pc.upload_file_minidump_flash2 = DotDict()
        pc.upload_file_minidump_flash2.json_dump = f2jd

        fake_processor = create_basic_fake_processor()

        rc = DotDict()
        rd = {}
        rule = SetWindowPos()
        action_result = rule.action(rc, rd, pc, fake_processor)

        assert action_result
        assert 'classifications' in pc
        assert 'skunk_works' in pc.classifications
        assert pc.classifications.skunk_works.classification == 'NtUserSetWindowPos | other'

    def test_action_case_2(self):
        """sentinel exsits in stack, plus one secondary"""
        pc = DotDict()
        pc.process_type = 'plugin'
        pijd = copy.deepcopy(cannonical_json_dump)
        pc.json_dump = pijd
        pc.json_dump['crashing_thread']['frames'][2]['function'] = \
            'NtUserSetWindowPos'
        pc.json_dump['crashing_thread']['frames'][4]['function'] = \
            'F_1378698112'
        f2jd = copy.deepcopy(cannonical_json_dump)
        pc.upload_file_minidump_flash2 = DotDict()
        pc.upload_file_minidump_flash2.json_dump = f2jd

        fake_processor = create_basic_fake_processor()

        rc = DotDict()
        rd = {}
        rule = SetWindowPos()
        action_result = rule.action(rc, rd, pc, fake_processor)

        assert action_result
        assert 'classifications' in pc
        assert 'skunk_works' in pc.classifications
        assert pc.classifications.skunk_works.classification == 'NtUserSetWindowPos | F_1378698112'

    def test_action_case_3(self):
        """nothing in 1st dump, sentinel and secondary in
        upload_file_minidump_flash2 dump"""
        pc = DotDict()
        pc.dump = DotDict()
        pijd = copy.deepcopy(cannonical_json_dump)
        pc.dump.json_dump = pijd
        f2jd = copy.deepcopy(cannonical_json_dump)
        pc.upload_file_minidump_flash2 = DotDict()
        pc.upload_file_minidump_flash2.json_dump = f2jd
        pc.upload_file_minidump_flash2.json_dump['crashing_thread']['frames'][2]['function'] = (
            'NtUserSetWindowPos'
        )
        pc.upload_file_minidump_flash2.json_dump['crashing_thread']['frames'][4]['function'] = (
            'F455544145'
        )

        fake_processor = create_basic_fake_processor()

        rc = DotDict()
        rd = {}
        rule = SetWindowPos()
        action_result = rule.action(rc, rd, pc, fake_processor)

        assert action_result
        assert 'classifications' in pc
        assert 'skunk_works' in pc.classifications
        assert pc.classifications.skunk_works.classification == 'NtUserSetWindowPos | F455544145'

    def test_action_case_4(self):
        """nothing in 1st dump, sentinel but no secondary in
        upload_file_minidump_flash2 dump"""
        pc = DotDict()
        pc.dump = DotDict()
        pijd = copy.deepcopy(cannonical_json_dump)
        pc.dump.json_dump = pijd
        f2jd = copy.deepcopy(cannonical_json_dump)
        pc.upload_file_minidump_flash2 = DotDict()
        pc.upload_file_minidump_flash2.json_dump = f2jd
        pc.upload_file_minidump_flash2.json_dump['crashing_thread']['frames'][2]['function'] = (
            'NtUserSetWindowPos'
        )

        fake_processor = create_basic_fake_processor()

        rc = DotDict()
        rd = {}
        rule = SetWindowPos()
        action_result = rule.action(rc, rd, pc, fake_processor)

        assert action_result
        assert 'classifications' in pc
        assert 'skunk_works' in pc.classifications
        assert pc.classifications.skunk_works.classification == 'NtUserSetWindowPos | other'

    def test_action_case_5(self):
        """nothing in either dump"""
        pc = DotDict()
        pc.dump = DotDict()
        pijd = copy.deepcopy(cannonical_json_dump)
        pc.dump.json_dump = pijd
        f2jd = copy.deepcopy(cannonical_json_dump)
        pc.upload_file_minidump_flash2 = DotDict()
        pc.upload_file_minidump_flash2.json_dump = f2jd

        fake_processor = create_basic_fake_processor()

        rc = DotDict()
        rd = {}
        rule = SetWindowPos()
        action_result = rule.action(rc, rd, pc, fake_processor)

        assert not action_result
        assert 'classifications' not in pc
