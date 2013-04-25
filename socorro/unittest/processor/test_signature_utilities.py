# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock

import socorro.processor.signature_utilities as sig
import socorro.lib.util as sutil

from socorro.database.transaction_executor import TransactionExecutor
from socorro.lib.util import DotDict
from socorro.processor.signature_utilities import JavaSignatureTool

import re

from mock import (Mock, patch, call)


class BaseTestClass(unittest.TestCase):

    def assert_equal_with_nicer_output (self, expected, received):
        self.assertEqual(
            expected,
            received,
            'expected:\n%s\nbut got:\n%s' % (expected, received)
        )

class TestCSignatureTool(BaseTestClass):

    @staticmethod
    def setup_config_C_sig_tool(
        ig='ignored1',
        pr='pre1|pre2',
        si='fnNeedNumber',
        ss=('sentinel', ('sentinel2', lambda x: 'ff' in x)),
    ):
        config = sutil.DotDict()
        config.logger = sutil.FakeLogger()
        config.irrelevant_signature_re = ig
        config.prefix_signature_re = pr
        config.signatures_with_line_numbers_re = si
        config.signature_sentinels = ss
        s = sig.CSignatureTool(config)
        return s, config

    @staticmethod
    def setup_db_C_sig_tool(
        ig='ignored1',
        pr='pre1|pre2',
        si='fnNeedNumber',
        ss=('sentinel', "('sentinel2', lambda x: 'ff' in x)")
    ):
        config = sutil.DotDict()
        config.logger = sutil.FakeLogger()
        config.database_class = mock.MagicMock()
        config.transaction_executor_class = TransactionExecutor
        patch_target = 'socorro.processor.signature_utilities.' \
                       'execute_query_fetchall'
        with mock.patch(patch_target) as mocked_query:
            # these become the results of four successive calls to
            # execute_query_fetchall
            mocked_query.side_effect = [
                [(pr,),],
                [(ig,), ],
                [(si,), ],
                [(x,) for x in ss],
            ]
            s = sig.CSignatureToolDB(config)
            return s, config


    def test_C_config_tool_init(self):
        """test_C_config_tool_init: constructor test"""
        expectedRegEx = sutil.DotDict()
        expectedRegEx.irrelevant_signature_re = re.compile('ignored1')
        expectedRegEx.prefix_signature_re = re.compile('pre1|pre2')
        expectedRegEx.signatures_with_line_numbers_re = re.compile(
            'fnNeedNumber'
        )
        fixupSpace = re.compile(r' (?=[\*&,])')
        fixupComma = re.compile(r',(?! )')
        fixupInteger = re.compile(r'(<|, )(\d+)([uUlL]?)([^\w])')

        s, c = self.setup_config_C_sig_tool(
            expectedRegEx.irrelevant_signature_re,
            expectedRegEx.prefix_signature_re,
            expectedRegEx.signatures_with_line_numbers_re
        )

        self.assert_equal_with_nicer_output(c, s.config)
        self.assert_equal_with_nicer_output(
            expectedRegEx.irrelevant_signature_re,
            s.irrelevant_signature_re
        )
        self.assert_equal_with_nicer_output(
            expectedRegEx.prefix_signature_re,
            s.prefix_signature_re
        )
        self.assert_equal_with_nicer_output(
            expectedRegEx.signatures_with_line_numbers_re,
            s.signatures_with_line_numbers_re
        )
        self.assert_equal_with_nicer_output(fixupSpace, s.fixup_space)
        self.assert_equal_with_nicer_output(fixupComma, s.fixup_comma)
        self.assert_equal_with_nicer_output(fixupInteger, s.fixup_integer)

    def test_C_db_tool_init(self):
        """test_C_db_tool_init: constructor test"""
        expectedRegEx = sutil.DotDict()
        expectedRegEx.irrelevant_signature_re = re.compile('ignored1')
        expectedRegEx.prefix_signature_re = re.compile('pre1|pre2')
        expectedRegEx.signatures_with_line_numbers_re = re.compile(
            'fnNeedNumber'
        )
        fixupSpace = re.compile(r' (?=[\*&,])')
        fixupComma = re.compile(r',(?! )')
        fixupInteger = re.compile(r'(<|, )(\d+)([uUlL]?)([^\w])')

        s, c = self.setup_db_C_sig_tool()

        self.assert_equal_with_nicer_output(c, s.config)
        self.assert_equal_with_nicer_output(
            expectedRegEx.irrelevant_signature_re,
            s.irrelevant_signature_re
        )
        self.assert_equal_with_nicer_output(
            expectedRegEx.prefix_signature_re,
            s.prefix_signature_re
        )
        self.assert_equal_with_nicer_output(
            expectedRegEx.signatures_with_line_numbers_re,
            s.signatures_with_line_numbers_re
        )
        self.assert_equal_with_nicer_output(fixupSpace, s.fixup_space)
        self.assert_equal_with_nicer_output(fixupComma, s.fixup_comma)
        self.assert_equal_with_nicer_output(fixupInteger, s.fixup_integer)


    def test_normalize(self):
        """test_normalize: bunch of variations"""
        s, c = self.setup_config_C_sig_tool()
        a = [
            (('module', 'fn', 'source', '23', '0xFFF'), 'fn'),
            (('module', 'fnNeedNumber', 's', '23', '0xFFF'),
             'fnNeedNumber:23'),
            (('module', 'f( *s)', 's', '23', '0xFFF'), 'f(*s)'),
            (('module', 'f( &s)', 's', '23', '0xFFF'), 'f(&s)'),
            (('module', 'f( *s , &n)', 's', '23', '0xFFF'), 'f(*s, &n)'),
            # this next one looks like a bug to me, but perhaps the situation
            # never comes up
            #(('module', 'f(  *s , &n)', 's', '23', '0xFFF'), 'f(*s, &n)'),
            (('module', 'f3(s,t,u)', 's', '23', '0xFFF'), 'f3(s, t, u)'),
            (('module', 'f<3>(s,t,u)', 's', '23', '0xFFF'), 'f<int>(s, t, u)'),
            (('module', '', 'source/', '23', '0xFFF'), 'source#23'),
            (('module', '', 'source\\', '23', '0xFFF'), 'source#23'),
            (('module', '', '/a/b/c/source', '23', '0xFFF'), 'source#23'),
            (('module', '', '\\a\\b\\c\\source', '23', '0xFFF'), 'source#23'),
            (('module', '', '\\a\\b\\c\\source', '23', '0xFFF'), 'source#23'),
            (('module', '', '\\a\\b\\c\\source', '', '0xFFF'), 'module@0xFFF'),
            (('module', '', '', '23', '0xFFF'), 'module@0xFFF'),
            (('module', '', '', '', '0xFFF'), 'module@0xFFF'),
            ((None, '', '', '', '0xFFF'), '@0xFFF'),
        ]
        for args, e in a:
            r = s.normalize_signature(*args)
            self.assert_equal_with_nicer_output(e,r)

    def test_generate_1(self):
        """test_generate_1: simple"""
        for s, c in (self.setup_config_C_sig_tool('a|b|c', 'd|e|f'),
                     self.setup_db_C_sig_tool('a|b|c', 'd|e|f')):
            a = [x for x in 'abcdefghijklmnopqrstuvwxyz']
            e = 'd | e | f | g'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e,sig)

            a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
            e = 'd | e | f | g'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e,sig)

    def test_generate_2(self):
        """test_generate_2: hang"""
        for s, c in (self.setup_config_C_sig_tool('a|b|c', 'd|e|f'),
                     self.setup_db_C_sig_tool('a|b|c', 'd|e|f')):
            a = [x for x in 'abcdefghijklmnopqrstuvwxyz']
            e = 'hang | d | e | f | g'
            sig, notes = s.generate(a, hang_type=-1)
            self.assert_equal_with_nicer_output(e,sig)

            a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
            e = 'hang | d | e | f | g'
            sig, notes = s.generate(a, hang_type=-1)
            self.assert_equal_with_nicer_output(e,sig)

            a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
            e = 'd | e | f | g'
            sig, notes = s.generate(a, hang_type=0)
            self.assert_equal_with_nicer_output(e,sig)

            a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
            e = 'chromehang | d | e | f | g'
            sig, notes = s.generate(a, hang_type=1)
            self.assert_equal_with_nicer_output(e,sig)


    def test_generate_2a(self):
        """test_generate_2a: way too long"""
        for s, c in (self.setup_config_C_sig_tool('a|b|c', 'd|e|f'),
                     self.setup_db_C_sig_tool('a|b|c', 'd|e|f')):
            a = [x for x in 'abcdefghijklmnopqrstuvwxyz']
            a[3] = a[3] * 70
            a[4] = a[4] * 70
            a[5] = a[5] * 70
            a[6] = a[6] * 70
            a[7] = a[7] * 70
            e = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddd" \
                "dddddddddddd " \
                "| eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee" \
                "eeeeeeeeeeeeee " \
                "| ffffffffffffffffffffffffffffffffffffffffffffffffffffffff" \
                "ffffffffffffff | ggggggggggggggggggggggggggggggggg..."
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e,sig)
            e = "hang | ddddddddddddddddddddddddddddddddddddddddddddddddddd" \
                "ddddddddddddddddddd " \
                "| eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee" \
                "eeeeeeeeeeeeee " \
                "| ffffffffffffffffffffffffffffffffffffffffffffffffffffffff" \
                "ffffffffffffff | gggggggggggggggggggggggggg..."
            sig, notes = s.generate(a, hang_type=-1)
            self.assert_equal_with_nicer_output(e,sig)

    def test_generate_3(self):
        """test_generate_3: simple sentinel"""
        for s, c in (self.setup_config_C_sig_tool('a|b|c', 'd|e|f'),
                     self.setup_db_C_sig_tool('a|b|c', 'd|e|f')):
            a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
            a[7] = 'sentinel'
            e = 'sentinel'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e,sig)

            s, c  = self.setup_config_C_sig_tool('a|b|c|sentinel', 'd|e|f')
            e = 'f | e | d | i'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e,sig)

    def test_generate_4(self):
        """test_generate_4: tuple sentinel"""
        for s, c in (self.setup_config_C_sig_tool('a|b|c', 'd|e|f'),
                     self.setup_db_C_sig_tool('a|b|c', 'd|e|f')):
            a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
            a[7] = 'sentinel2'
            e = 'd | e | f | g'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e,sig)

        for s, c in (self.setup_config_C_sig_tool('a|b|c', 'd|e|f'),
                     self.setup_db_C_sig_tool('a|b|c', 'd|e|f')):
            a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
            a[7] = 'sentinel2'
            a[22] = 'ff'
            e = 'sentinel2'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e,sig)

        for s, c in (self.setup_config_C_sig_tool('a|b|c|sentinel2', 'd|e|f'),
                     self.setup_db_C_sig_tool('a|b|c|sentinel2', 'd|e|f')):
            a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
            a[7] = 'sentinel2'
            a[22] = 'ff'
            e = 'f | e | d | i'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e,sig)


class TestCSignatureToolDB(BaseTestClass):

    @staticmethod
    def setup_config():
        config = sutil.DotDict()
        config.logger = sutil.FakeLogger()
        config.database_class = Mock()
        config.transaction_executor_class = Mock()
        return config


    def test__init__(self):
        """This class ought to load its values from the database at the time
        of initialization. This test assures us that it really happens."""
        query_results = [
            (('@0x0',), ('.*abort',), ('(libxul\.so|xul\.dll|XUL)@0x.*',)),
            (('@0x[0-9a-fA-F]{2,}',), ('app_process@0x.*',), ('libc\.so@.*',)),
            (('js_Interpret',),),
            (('_purecall',),
             ("('sentinel', lambda x: 'mmm' in x)",),
             ('fake sentinel',),),
        ]
        def query_results_mock_fn(dummy1, dummy2, dummy3=None):
            return query_results.pop(0)
        expected_re_dict = {
            'signatures_with_line_numbers_re': 'js_Interpret',
            'prefix_signature_re':
                '@0x0|.*abort|(libxul\.so|xul\.dll|XUL)@0x.*',
            'irrelevant_signature_re':
                '@0x[0-9a-fA-F]{2,}|app_process@0x.*|libc\.so@.*',
            'signature_sentinels': [
                '_purecall',
                ('sentinel', lambda x: 'mmm' in x),
                'fake sentinel',
            ]
        }
        with patch(
            'socorro.processor.signature_utilities.execute_query_fetchall'
        ) as execute_query_mock:
            execute_query_mock.side_effect = query_results_mock_fn
            config = self.setup_config()
            c_sig_tool = sig.CSignatureToolDB(config)
            c_sig_tool._read_signature_rules_from_database(Mock())

            config.database_class.assert_called_once_with(config)
            config.transaction_executor_class.assert_called_once_with(
                config,
                c_sig_tool.database,
                None
            )
            self.assertEqual(
                c_sig_tool.signatures_with_line_numbers_re.pattern,
                expected_re_dict['signatures_with_line_numbers_re']
            )
            self.assertEqual(
                c_sig_tool.irrelevant_signature_re.pattern,
                expected_re_dict['irrelevant_signature_re']
            )
            self.assertEqual(
                c_sig_tool.prefix_signature_re.pattern,
                expected_re_dict['prefix_signature_re']
            )
            self.assertEqual(len(c_sig_tool.signature_sentinels), 3)
            self.assertEqual(
                c_sig_tool.signature_sentinels[0],
                expected_re_dict['signature_sentinels'][0]
            )
            self.assertEqual(
                c_sig_tool.signature_sentinels[1][0],
                expected_re_dict['signature_sentinels'][1][0]
            )
            self.assertEqual(
                c_sig_tool.signature_sentinels[2],
                expected_re_dict['signature_sentinels'][2]
            )
            actual_fn = c_sig_tool.signature_sentinels[1][1]
            # can't test directly for equality of lambdas - so test
            # functionality instead
            self.assertTrue(
                actual_fn(['x', 'y', 'z', 'mmm', 'i', 'j', 'k'])
            )
            self.assertFalse(
                actual_fn(['x', 'y', 'z', 'i', 'j', 'k'])
            )


class TestJavaSignatureTool(BaseTestClass):
    def test_generate_signature_1(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 17
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = "EMPTY: Java stack trace not in expected format"
        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: stack trace not '
             'in expected format']
        self.assert_equal_with_nicer_output(e, notes)

    def test_generate_signature_2(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('SomeJavaException: totally made up  \n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java:666)')
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('SomeJavaException: totally made up '
             'at org.mozilla.lars.myInvention('
             'larsFile.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = []
        self.assert_equal_with_nicer_output(e, notes)

    def test_generate_signature_3(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('SomeJavaException: totally made up  \n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java)')
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('SomeJavaException: totally made up '
             'at org.mozilla.lars.myInvention('
             'larsFile.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = []
        self.assert_equal_with_nicer_output(e, notes)

    def test_generate_signature_4(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('   SomeJavaException: %s  \n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java)' % ('t'*1000))
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('SomeJavaException: '
             'at org.mozilla.lars.myInvention('
             'larsFile.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: dropped Java exception description due to '
             'length']
        self.assert_equal_with_nicer_output(e, notes)

    def test_generate_signature_4_2(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('   SomeJavaException: %s  \n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java:1234)' % ('t'*1000))
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('SomeJavaException: '
             'at org.mozilla.lars.myInvention('
             'larsFile.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: dropped Java exception description due to '
             'length']
        self.assert_equal_with_nicer_output(e, notes)

    def test_generate_signature_5(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('   SomeJavaException\n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java:1234)')
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('SomeJavaException: '
             'at org.mozilla.lars.myInvention('
             'larsFile.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: stack trace line 1 is '
             'not in the expected format']
        self.assert_equal_with_nicer_output(e, notes)

    def test_generate_signature_6(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 'SomeJavaException: totally made up  \n'
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = 'SomeJavaException: totally made up'

        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: stack trace line 2 is missing']
        self.assert_equal_with_nicer_output(e, notes)

    def test_generate_signature_7(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 'SomeJavaException: totally made up  '
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = 'SomeJavaException: totally made up'
        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: stack trace line 2 is missing']
        self.assert_equal_with_nicer_output(e, notes)

    def test_generate_signature_8(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 'SomeJavaException: totally made up  '
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = 'SomeJavaException: totally made up'
        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: stack trace line 2 is missing']
        self.assert_equal_with_nicer_output(e, notes)

    def test_generate_signature_9(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('   SomeJavaException: totally made up  \n'
                            'at org.mozilla.lars.myInvention('
                            '%slarsFile.java:1234)' % ('t'*1000))
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('SomeJavaException: '
             'at org.mozilla.lars.myInvention('
             '%s...' % ('t' * 201))
        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: dropped Java exception description due to '
             'length',
             'SignatureTool: signature truncated due to length']
        self.assert_equal_with_nicer_output(e, notes)

    def test_generate_signature_10_no_interference(self):
        """In general addresses of the form @xxxxxxxx are to be replaced with
        the literal "<addr>", however in this case, the hex address is not in
        the expected location and should therefore be left alone"""
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('SomeJavaException: totally made up  \n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java:@abef1234)')
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = ('SomeJavaException totally made up '
             'at org.mozilla.lars.myInvention('
             'larsFile.java:@abef1234)')
        self.assert_equal_with_nicer_output(e, sig)
        self.assert_equal_with_nicer_output([], notes)

    def test_generate_signature_11_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """java.lang.IllegalArgumentException: Given view not a child of android.widget.AbsoluteLayout@4054b560
	at android.view.ViewGroup.updateViewLayout(ViewGroup.java:1968)
	at org.mozilla.gecko.GeckoApp.repositionPluginViews(GeckoApp.java:1492)
	at org.mozilla.gecko.GeckoApp.repositionPluginViews(GeckoApp.java:1475)
	at org.mozilla.gecko.gfx.LayerController$2.run(LayerController.java:269)
	at android.os.Handler.handleCallback(Handler.java:587)
	at android.os.Handler.dispatchMessage(Handler.java:92)
	at android.os.Looper.loop(Looper.java:150)
	at org.mozilla.gecko.GeckoApp$32.run(GeckoApp.java:1670)
	at android.os.Handler.handleCallback(Handler.java:587)
	at android.os.Handler.dispatchMessage(Handler.java:92)
	at android.os.Looper.loop(Looper.java:150)
	at android.app.ActivityThread.main(ActivityThread.java:4293)
	at java.lang.reflect.Method.invokeNative(Native Method)
	at java.lang.reflect.Method.invoke(Method.java:507)
	at com.android.internal.os.ZygoteInit$MethodAndArgsCaller.run(ZygoteInit.java:849)
	at com.android.internal.os.ZygoteInit.main(ZygoteInit.java:607)
	at dalvik.system.NativeStart.main(Native Method)"""
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('java.lang.IllegalArgumentException: '
             'Given view not a child of android.widget.AbsoluteLayout@<addr>: '
             'at android.view.ViewGroup.updateViewLayout(ViewGroup.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = []
        self.assert_equal_with_nicer_output(e, notes)


    def test_generate_signature_12_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """java.lang.IllegalArgumentException: Given view not a child of android.widget.AbsoluteLayout@4054b560
	at android.view.ViewGroup.updateViewLayout(ViewGroup.java:1968)
	at org.mozilla.gecko.GeckoApp.repositionPluginViews(GeckoApp.java:1492)
	at org.mozilla.gecko.GeckoApp.repositionPluginViews(GeckoApp.java:1475)
	at org.mozilla.gecko.gfx.LayerController$2.run(LayerController.java:269)
	at android.os.Handler.handleCallback(Handler.java:587)
	at android.os.Handler.dispatchMessage(Handler.java:92)
	at android.os.Looper.loop(Looper.java:150)
	at org.mozilla.gecko.GeckoApp$32.run(GeckoApp.java:1670)
	at android.os.Handler.handleCallback(Handler.java:587)
	at android.os.Handler.dispatchMessage(Handler.java:92)
	at android.os.Looper.loop(Looper.java:150)
	at android.app.ActivityThread.main(ActivityThread.java:4293)
	at java.lang.reflect.Method.invokeNative(Native Method)
	at java.lang.reflect.Method.invoke(Method.java:507)
	at com.android.internal.os.ZygoteInit$MethodAndArgsCaller.run(ZygoteInit.java:849)
	at com.android.internal.os.ZygoteInit.main(ZygoteInit.java:607)
	at dalvik.system.NativeStart.main(Native Method)"""
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('java.lang.IllegalArgumentException: '
             'Given view not a child of android.widget.AbsoluteLayout@<addr>: '
             'at android.view.ViewGroup.updateViewLayout(ViewGroup.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = []
        self.assert_equal_with_nicer_output(e, notes)

    def test_generate_signature_13_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """java.lang.IllegalArgumentException: Receiver not registered: org.mozilla.gecko.GeckoConnectivityReceiver@2c004bc8
	at android.app.LoadedApk.forgetReceiverDispatcher(LoadedApk.java:628)
	at android.app.ContextImpl.unregisterReceiver(ContextImpl.java:1066)
	at android.content.ContextWrapper.unregisterReceiver(ContextWrapper.java:354)
	at org.mozilla.gecko.GeckoConnectivityReceiver.unregisterFor(GeckoConnectivityReceiver.java:92)
	at org.mozilla.gecko.GeckoApp.onApplicationPause(GeckoApp.java:2104)
	at org.mozilla.gecko.GeckoApplication.onActivityPause(GeckoApplication.java:43)
	at org.mozilla.gecko.GeckoActivity.onPause(GeckoActivity.java:24)
	at android.app.Activity.performPause(Activity.java:4563)
	at android.app.Instrumentation.callActivityOnPause(Instrumentation.java:1195)
	at android.app.ActivityThread.performNewIntents(ActivityThread.java:2064)
	at android.app.ActivityThread.handleNewIntent(ActivityThread.java:2075)
	at android.app.ActivityThread.access$1400(ActivityThread.java:127)
	at android.app.ActivityThread$H.handleMessage(ActivityThread.java:1205)
	at android.os.Handler.dispatchMessage(Handler.java:99)
	at android.os.Looper.loop(Looper.java:137)
	at android.app.ActivityThread.main(ActivityThread.java:4441)
	at java.lang.reflect.Method.invokeNative(Native Method)
	at java.lang.reflect.Method.invoke(Method.java:511)
	at com.android.internal.os.ZygoteInit$MethodAndArgsCaller.run(ZygoteInit.java:784)
	at com.android.internal.os.ZygoteInit.main(ZygoteInit.java:551)
	at dalvik.system.NativeStart.main(Native Method)"""
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('java.lang.IllegalArgumentException: '
             'Receiver not registered: '
             'org.mozilla.gecko.GeckoConnectivityReceiver@<addr>: '
             'at android.app.LoadedApk.forgetReceiverDispatcher'
             '(LoadedApk.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = []
        self.assert_equal_with_nicer_output(e, notes)

    def test_generate_signature_14_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """android.view.WindowManager$BadTokenException: Unable to add window -- token android.os.BinderProxy@406237c0 is not valid; is your activity running?
	at android.view.ViewRoot.setView(ViewRoot.java:533)
	at android.view.WindowManagerImpl.addView(WindowManagerImpl.java:202)
	at android.view.WindowManagerImpl.addView(WindowManagerImpl.java:116)
	at android.view.Window$LocalWindowManager.addView(Window.java:424)
	at android.app.ActivityThread.handleResumeActivity(ActivityThread.java:2174)
	at android.app.ActivityThread.handleLaunchActivity(ActivityThread.java:1672)
	at android.app.ActivityThread.access$1500(ActivityThread.java:117)
	at android.app.ActivityThread$H.handleMessage(ActivityThread.java:935)
	at android.os.Handler.dispatchMessage(Handler.java:99)
	at android.os.Looper.loop(Looper.java:130)
	at android.app.ActivityThread.main(ActivityThread.java:3687)
	at java.lang.reflect.Method.invokeNative(Native Method)
	at java.lang.reflect.Method.invoke(Method.java:507)
	at com.android.internal.os.ZygoteInit$MethodAndArgsCaller.run(ZygoteInit.java:867)
	at com.android.internal.os.ZygoteInit.main(ZygoteInit.java:625)
	at dalvik.system.NativeStart.main(Native Method)
"""
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('android.view.WindowManager$BadTokenException: '
             'Unable to add window -- token android.os.BinderProxy@<addr> '
             'is not valid; is your activity running? '
             'at android.view.ViewRoot.setView(ViewRoot.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = []
        self.assert_equal_with_nicer_output(e, notes)

    def test_generate_signature_15_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """java.lang.IllegalArgumentException: Receiver not registered: org.mozilla.gecko.GeckoNetworkManager@405afea8
	at android.app.LoadedApk.forgetReceiverDispatcher(LoadedApk.java:610)
	at android.app.ContextImpl.unregisterReceiver(ContextImpl.java:883)
	at android.content.ContextWrapper.unregisterReceiver(ContextWrapper.java:331)
	at org.mozilla.gecko.GeckoNetworkManager.stopListening(GeckoNetworkManager.java:141)
	at org.mozilla.gecko.GeckoNetworkManager.stop(GeckoNetworkManager.java:136)
	at org.mozilla.gecko.GeckoApp.onApplicationPause(GeckoApp.java:2130)
	at org.mozilla.gecko.GeckoApplication.onActivityPause(GeckoApplication.java:55)
	at org.mozilla.gecko.GeckoActivity.onPause(GeckoActivity.java:22)
	at org.mozilla.gecko.GeckoApp.onPause(GeckoApp.java:1948)
	at android.app.Activity.performPause(Activity.java:3877)
	at android.app.Instrumentation.callActivityOnPause(Instrumentation.java:1191)
	at android.app.ActivityThread.performPauseActivity(ActivityThread.java:2345)
	at android.app.ActivityThread.performPauseActivity(ActivityThread.java:2315)
	at android.app.ActivityThread.handlePauseActivity(ActivityThread.java:2295)
	at android.app.ActivityThread.access$1700(ActivityThread.java:117)
	at android.app.ActivityThread$H.handleMessage(ActivityThread.java:942)
	at android.os.Handler.dispatchMessage(Handler.java:99)
	at android.os.Looper.loop(Looper.java:130)
	at android.app.ActivityThread.main(ActivityThread.java:3691)
	at java.lang.reflect.Method.invokeNative(Native Method)
	at java.lang.reflect.Method.invoke(Method.java:507)
	at com.android.internal.os.ZygoteInit$MethodAndArgsCaller.run(ZygoteInit.java:907)
	at com.android.internal.os.ZygoteInit.main(ZygoteInit.java:665)
	at dalvik.system.NativeStart.main(Native Method)
"""
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('java.lang.IllegalArgumentException: '
             'Receiver not registered: '
             'org.mozilla.gecko.GeckoNetworkManager@<addr>: '
             'at android.app.LoadedApk.forgetReceiverDispatcher(LoadedApk.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = []
        self.assert_equal_with_nicer_output(e, notes)
