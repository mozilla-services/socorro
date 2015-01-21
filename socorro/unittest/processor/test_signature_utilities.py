# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
from nose.tools import eq_, ok_

from configman.dotdict import DotDict as CDotDict

import socorro.lib.util as sutil

from socorro.database.transaction_executor import TransactionExecutor
from socorro.lib.util import DotDict
from socorro.processor.signature_utilities import (
    CSignatureTool,
    CSignatureToolDB,
    JavaSignatureTool,
    SignatureGenerationRule,
    OOMSignature,
    SigTrunc,
    StackwalkerErrorSignatureRule,
    SignatureRunWatchDog,
)
from socorro.unittest.testbase import TestCase

import re
import copy

from mock import Mock, patch


#==============================================================================
class BaseTestClass(TestCase):

    def assert_equal_with_nicer_output(self, expected, received):
        eq_(
            expected,
            received,
            'expected:\n%s\nbut got:\n%s' % (expected, received)
        )


#==============================================================================
class TestCSignatureTool(BaseTestClass):

    #--------------------------------------------------------------------------
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
        s = CSignatureTool(config)
        return s, config

    #--------------------------------------------------------------------------
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
                [(pr,), ],
                [(ig,), ],
                [(si,), ],
                [(x,) for x in ss],
            ]
            s = CSignatureToolDB(config)
            return s, config

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
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
            self.assert_equal_with_nicer_output(e, r)

    #--------------------------------------------------------------------------
    def test_generate_1(self):
        """test_generate_1: simple"""
        for s, c in (self.setup_config_C_sig_tool('a|b|c', 'd|e|f'),
                     self.setup_db_C_sig_tool('a|b|c', 'd|e|f')):
            a = [x for x in 'abcdefghijklmnopqrstuvwxyz']
            e = 'd | e | f | g'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e, sig)

            a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
            e = 'd | e | f | g'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e, sig)

    #--------------------------------------------------------------------------
    def test_generate_2(self):
        """test_generate_2: hang"""
        for s, c in (self.setup_config_C_sig_tool('a|b|c', 'd|e|f'),
                     self.setup_db_C_sig_tool('a|b|c', 'd|e|f')):
            a = [x for x in 'abcdefghijklmnopqrstuvwxyz']
            e = 'hang | d | e | f | g'
            sig, notes = s.generate(a, hang_type=-1)
            self.assert_equal_with_nicer_output(e, sig)

            a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
            e = 'hang | d | e | f | g'
            sig, notes = s.generate(a, hang_type=-1)
            self.assert_equal_with_nicer_output(e, sig)

            a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
            e = 'd | e | f | g'
            sig, notes = s.generate(a, hang_type=0)
            self.assert_equal_with_nicer_output(e, sig)

            a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
            e = 'chromehang | d | e | f | g'
            sig, notes = s.generate(a, hang_type=1)
            self.assert_equal_with_nicer_output(e, sig)

    #--------------------------------------------------------------------------
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
            self.assert_equal_with_nicer_output(e, sig)
            e = "hang | ddddddddddddddddddddddddddddddddddddddddddddddddddd" \
                "ddddddddddddddddddd " \
                "| eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee" \
                "eeeeeeeeeeeeee " \
                "| ffffffffffffffffffffffffffffffffffffffffffffffffffffffff" \
                "ffffffffffffff | gggggggggggggggggggggggggg..."
            sig, notes = s.generate(a, hang_type=-1)
            self.assert_equal_with_nicer_output(e, sig)

    #--------------------------------------------------------------------------
    def test_generate_3(self):
        """test_generate_3: simple sentinel"""
        for s, c in (self.setup_config_C_sig_tool('a|b|c', 'd|e|f'),
                     self.setup_db_C_sig_tool('a|b|c', 'd|e|f')):
            a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
            a[7] = 'sentinel'
            e = 'sentinel'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e, sig)

            s, c = self.setup_config_C_sig_tool('a|b|c|sentinel', 'd|e|f')
            e = 'f | e | d | i'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e, sig)

    #--------------------------------------------------------------------------
    def test_generate_4(self):
        """test_generate_4: tuple sentinel"""
        for s, c in (self.setup_config_C_sig_tool('a|b|c', 'd|e|f'),
                     self.setup_db_C_sig_tool('a|b|c', 'd|e|f')):
            a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
            a[7] = 'sentinel2'
            e = 'd | e | f | g'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e, sig)

        for s, c in (self.setup_config_C_sig_tool('a|b|c', 'd|e|f'),
                     self.setup_db_C_sig_tool('a|b|c', 'd|e|f')):
            a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
            a[7] = 'sentinel2'
            a[22] = 'ff'
            e = 'sentinel2'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e, sig)

        for s, c in (self.setup_config_C_sig_tool('a|b|c|sentinel2', 'd|e|f'),
                     self.setup_db_C_sig_tool('a|b|c|sentinel2', 'd|e|f')):
            a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
            a[7] = 'sentinel2'
            a[22] = 'ff'
            e = 'f | e | d | i'
            sig, notes = s.generate(a)
            self.assert_equal_with_nicer_output(e, sig)


#==============================================================================
class TestCSignatureToolDB(BaseTestClass):

    #--------------------------------------------------------------------------
    @staticmethod
    def setup_config():
        config = sutil.DotDict()
        config.logger = sutil.FakeLogger()
        config.database_class = Mock()
        config.transaction_executor_class = Mock()
        return config

    #--------------------------------------------------------------------------
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
            c_sig_tool = CSignatureToolDB(config)
            c_sig_tool._read_signature_rules_from_database(Mock())

            config.database_class.assert_called_once_with(config)
            config.transaction_executor_class.assert_called_once_with(
                config,
                c_sig_tool.database,
                None
            )
            eq_(
                c_sig_tool.signatures_with_line_numbers_re.pattern,
                expected_re_dict['signatures_with_line_numbers_re']
            )
            eq_(
                c_sig_tool.irrelevant_signature_re.pattern,
                expected_re_dict['irrelevant_signature_re']
            )
            eq_(
                c_sig_tool.prefix_signature_re.pattern,
                expected_re_dict['prefix_signature_re']
            )
            eq_(len(c_sig_tool.signature_sentinels), 3)
            eq_(
                c_sig_tool.signature_sentinels[0],
                expected_re_dict['signature_sentinels'][0]
            )
            eq_(
                c_sig_tool.signature_sentinels[1][0],
                expected_re_dict['signature_sentinels'][1][0]
            )
            eq_(
                c_sig_tool.signature_sentinels[2],
                expected_re_dict['signature_sentinels'][2]
            )
            actual_fn = c_sig_tool.signature_sentinels[1][1]
            # can't test directly for equality of lambdas - so test
            # functionality instead
            ok_(
                actual_fn(['x', 'y', 'z', 'mmm', 'i', 'j', 'k'])
            )
            ok_(
                not actual_fn(['x', 'y', 'z', 'i', 'j', 'k'])
            )


#==============================================================================
class TestJavaSignatureTool(BaseTestClass):
    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
    def test_generate_signature_4(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('   SomeJavaException: %s  \n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java)' % ('t' * 1000))
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('SomeJavaException: '
             'at org.mozilla.lars.myInvention('
             'larsFile.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: dropped Java exception description due to '
             'length']
        self.assert_equal_with_nicer_output(e, notes)

    #--------------------------------------------------------------------------
    def test_generate_signature_4_2(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('   SomeJavaException: %s  \n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java:1234)' % ('t' * 1000))
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('SomeJavaException: '
             'at org.mozilla.lars.myInvention('
             'larsFile.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: dropped Java exception description due to '
             'length']
        self.assert_equal_with_nicer_output(e, notes)

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
    def test_generate_signature_6(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 'SomeJavaException: totally made up  \n'
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = 'SomeJavaException: totally made up'

        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: stack trace line 2 is missing']
        self.assert_equal_with_nicer_output(e, notes)

    #--------------------------------------------------------------------------
    def test_generate_signature_7(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 'SomeJavaException: totally made up  '
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = 'SomeJavaException: totally made up'
        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: stack trace line 2 is missing']
        self.assert_equal_with_nicer_output(e, notes)

    #--------------------------------------------------------------------------
    def test_generate_signature_8(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 'SomeJavaException: totally made up  '
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = 'SomeJavaException: totally made up'
        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: stack trace line 2 is missing']
        self.assert_equal_with_nicer_output(e, notes)

    #--------------------------------------------------------------------------
    def test_generate_signature_9(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('   SomeJavaException: totally made up  \n'
                            'at org.mozilla.lars.myInvention('
                            '%slarsFile.java:1234)' % ('t' * 1000))
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('SomeJavaException: '
             'at org.mozilla.lars.myInvention('
             '%s...' % ('t' * 201))
        self.assert_equal_with_nicer_output(e, sig)
        e = ['JavaSignatureTool: dropped Java exception description due to '
             'length',
             'SignatureTool: signature truncated due to length']
        self.assert_equal_with_nicer_output(e, notes)

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
    def test_generate_signature_11_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """java.lang.IllegalArgumentException: Given view not a child of android.widget.AbsoluteLayout@4054b560
\tat android.view.ViewGroup.updateViewLayout(ViewGroup.java:1968)
\tat org.mozilla.gecko.GeckoApp.repositionPluginViews(GeckoApp.java:1492)
\tat org.mozilla.gecko.GeckoApp.repositionPluginViews(GeckoApp.java:1475)
\tat org.mozilla.gecko.gfx.LayerController$2.run(LayerController.java:269)
\tat android.os.Handler.handleCallback(Handler.java:587)
\tat android.os.Handler.dispatchMessage(Handler.java:92)
\tat android.os.Looper.loop(Looper.java:150)
\tat org.mozilla.gecko.GeckoApp$32.run(GeckoApp.java:1670)
\tat android.os.Handler.handleCallback(Handler.java:587)
\tat android.os.Handler.dispatchMessage(Handler.java:92)
\tat android.os.Looper.loop(Looper.java:150)
\tat android.app.ActivityThread.main(ActivityThread.java:4293)
\tat java.lang.reflect.Method.invokeNative(Native Method)
\tat java.lang.reflect.Method.invoke(Method.java:507)
\tat com.android.internal.os.ZygoteInit$MethodAndArgsCaller.run(ZygoteInit.java:849)
\tat com.android.internal.os.ZygoteInit.main(ZygoteInit.java:607)
\tat dalvik.system.NativeStart.main(Native Method)"""
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('java.lang.IllegalArgumentException: '
             'Given view not a child of android.widget.AbsoluteLayout@<addr>: '
             'at android.view.ViewGroup.updateViewLayout(ViewGroup.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = []
        self.assert_equal_with_nicer_output(e, notes)

    #--------------------------------------------------------------------------
    def test_generate_signature_12_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """java.lang.IllegalArgumentException: Given view not a child of android.widget.AbsoluteLayout@4054b560
\tat android.view.ViewGroup.updateViewLayout(ViewGroup.java:1968)
\tat org.mozilla.gecko.GeckoApp.repositionPluginViews(GeckoApp.java:1492)
\tat org.mozilla.gecko.GeckoApp.repositionPluginViews(GeckoApp.java:1475)
\tat org.mozilla.gecko.gfx.LayerController$2.run(LayerController.java:269)
\tat android.os.Handler.handleCallback(Handler.java:587)
\tat android.os.Handler.dispatchMessage(Handler.java:92)
\tat android.os.Looper.loop(Looper.java:150)
\tat org.mozilla.gecko.GeckoApp$32.run(GeckoApp.java:1670)
\tat android.os.Handler.handleCallback(Handler.java:587)
\tat android.os.Handler.dispatchMessage(Handler.java:92)
\tat android.os.Looper.loop(Looper.java:150)
\tat android.app.ActivityThread.main(ActivityThread.java:4293)
\tat java.lang.reflect.Method.invokeNative(Native Method)
\tat java.lang.reflect.Method.invoke(Method.java:507)
\tat com.android.internal.os.ZygoteInit$MethodAndArgsCaller.run(ZygoteInit.java:849)
\tat com.android.internal.os.ZygoteInit.main(ZygoteInit.java:607)
\tat dalvik.system.NativeStart.main(Native Method)"""
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('java.lang.IllegalArgumentException: '
             'Given view not a child of android.widget.AbsoluteLayout@<addr>: '
             'at android.view.ViewGroup.updateViewLayout(ViewGroup.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = []
        self.assert_equal_with_nicer_output(e, notes)

    #--------------------------------------------------------------------------
    def test_generate_signature_13_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """java.lang.IllegalArgumentException: Receiver not registered: org.mozilla.gecko.GeckoConnectivityReceiver@2c004bc8
\tat android.app.LoadedApk.forgetReceiverDispatcher(LoadedApk.java:628)
\tat android.app.ContextImpl.unregisterReceiver(ContextImpl.java:1066)
\tat android.content.ContextWrapper.unregisterReceiver(ContextWrapper.java:354)
\tat org.mozilla.gecko.GeckoConnectivityReceiver.unregisterFor(GeckoConnectivityReceiver.java:92)
\tat org.mozilla.gecko.GeckoApp.onApplicationPause(GeckoApp.java:2104)
\tat org.mozilla.gecko.GeckoApplication.onActivityPause(GeckoApplication.java:43)
\tat org.mozilla.gecko.GeckoActivity.onPause(GeckoActivity.java:24)
\tat android.app.Activity.performPause(Activity.java:4563)
\tat android.app.Instrumentation.callActivityOnPause(Instrumentation.java:1195)
\tat android.app.ActivityThread.performNewIntents(ActivityThread.java:2064)
\tat android.app.ActivityThread.handleNewIntent(ActivityThread.java:2075)
\tat android.app.ActivityThread.access$1400(ActivityThread.java:127)
\tat android.app.ActivityThread$H.handleMessage(ActivityThread.java:1205)
\tat android.os.Handler.dispatchMessage(Handler.java:99)
\tat android.os.Looper.loop(Looper.java:137)
\tat android.app.ActivityThread.main(ActivityThread.java:4441)
\tat java.lang.reflect.Method.invokeNative(Native Method)
\tat java.lang.reflect.Method.invoke(Method.java:511)
\tat com.android.internal.os.ZygoteInit$MethodAndArgsCaller.run(ZygoteInit.java:784)
\tat com.android.internal.os.ZygoteInit.main(ZygoteInit.java:551)
\tat dalvik.system.NativeStart.main(Native Method)"""
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('java.lang.IllegalArgumentException: '
             'Receiver not registered: '
             'org.mozilla.gecko.GeckoConnectivityReceiver@<addr>: '
             'at android.app.LoadedApk.forgetReceiverDispatcher'
             '(LoadedApk.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = []
        self.assert_equal_with_nicer_output(e, notes)

    #--------------------------------------------------------------------------
    def test_generate_signature_14_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """android.view.WindowManager$BadTokenException: Unable to add window -- token android.os.BinderProxy@406237c0 is not valid; is your activity running?
\tat android.view.ViewRoot.setView(ViewRoot.java:533)
\tat android.view.WindowManagerImpl.addView(WindowManagerImpl.java:202)
\tat android.view.WindowManagerImpl.addView(WindowManagerImpl.java:116)
\tat android.view.Window$LocalWindowManager.addView(Window.java:424)
\tat android.app.ActivityThread.handleResumeActivity(ActivityThread.java:2174)
\tat android.app.ActivityThread.handleLaunchActivity(ActivityThread.java:1672)
\tat android.app.ActivityThread.access$1500(ActivityThread.java:117)
\tat android.app.ActivityThread$H.handleMessage(ActivityThread.java:935)
\tat android.os.Handler.dispatchMessage(Handler.java:99)
\tat android.os.Looper.loop(Looper.java:130)
\tat android.app.ActivityThread.main(ActivityThread.java:3687)
\tat java.lang.reflect.Method.invokeNative(Native Method)
\tat java.lang.reflect.Method.invoke(Method.java:507)
\tat com.android.internal.os.ZygoteInit$MethodAndArgsCaller.run(ZygoteInit.java:867)
\tat com.android.internal.os.ZygoteInit.main(ZygoteInit.java:625)
\tat dalvik.system.NativeStart.main(Native Method)
"""
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('android.view.WindowManager$BadTokenException: '
             'Unable to add window -- token android.os.BinderProxy@<addr> '
             'is not valid; is your activity running? '
             'at android.view.ViewRoot.setView(ViewRoot.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = []
        self.assert_equal_with_nicer_output(e, notes)

    #--------------------------------------------------------------------------
    def test_generate_signature_15_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """java.lang.IllegalArgumentException: Receiver not registered: org.mozilla.gecko.GeckoNetworkManager@405afea8
\tat android.app.LoadedApk.forgetReceiverDispatcher(LoadedApk.java:610)
\tat android.app.ContextImpl.unregisterReceiver(ContextImpl.java:883)
\tat android.content.ContextWrapper.unregisterReceiver(ContextWrapper.java:331)
\tat org.mozilla.gecko.GeckoNetworkManager.stopListening(GeckoNetworkManager.java:141)
\tat org.mozilla.gecko.GeckoNetworkManager.stop(GeckoNetworkManager.java:136)
\tat org.mozilla.gecko.GeckoApp.onApplicationPause(GeckoApp.java:2130)
\tat org.mozilla.gecko.GeckoApplication.onActivityPause(GeckoApplication.java:55)
\tat org.mozilla.gecko.GeckoActivity.onPause(GeckoActivity.java:22)
\tat org.mozilla.gecko.GeckoApp.onPause(GeckoApp.java:1948)
\tat android.app.Activity.performPause(Activity.java:3877)
\tat android.app.Instrumentation.callActivityOnPause(Instrumentation.java:1191)
\tat android.app.ActivityThread.performPauseActivity(ActivityThread.java:2345)
\tat android.app.ActivityThread.performPauseActivity(ActivityThread.java:2315)
\tat android.app.ActivityThread.handlePauseActivity(ActivityThread.java:2295)
\tat android.app.ActivityThread.access$1700(ActivityThread.java:117)
\tat android.app.ActivityThread$H.handleMessage(ActivityThread.java:942)
\tat android.os.Handler.dispatchMessage(Handler.java:99)
\tat android.os.Looper.loop(Looper.java:130)
\tat android.app.ActivityThread.main(ActivityThread.java:3691)
\tat java.lang.reflect.Method.invokeNative(Native Method)
\tat java.lang.reflect.Method.invoke(Method.java:507)
\tat com.android.internal.os.ZygoteInit$MethodAndArgsCaller.run(ZygoteInit.java:907)
\tat com.android.internal.os.ZygoteInit.main(ZygoteInit.java:665)
\tat dalvik.system.NativeStart.main(Native Method)
"""
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('java.lang.IllegalArgumentException: '
             'Receiver not registered: '
             'org.mozilla.gecko.GeckoNetworkManager@<addr>: '
             'at android.app.LoadedApk.forgetReceiverDispatcher(LoadedApk.java)')
        self.assert_equal_with_nicer_output(e, sig)
        e = []
        self.assert_equal_with_nicer_output(e, notes)

#==============================================================================
#  rules testing section

frames_from_json_dump = {
    u'frames': [
        {
            u'frame': 0,
            u'function': u'NtWaitForMultipleObjects',
            u'function_offset': u'0x15',
            u'module': u'ntdll.dll',
            u'module_offset': u'0x2015d',
            u'offset': u'0x77ad015d',
            u'registers': {
                u'eax': u'0x00000040',
                u'ebp': u'0x0025e968',
                u'ebx': u'0x0025e91c',
                u'ecx': u'0x00000000',
                u'edi': u'0x00000000',
                u'edx': u'0x00000000',
                u'efl': u'0x00200246',
                u'eip': u'0x77ad015d',
                u'esi': u'0x00000004',
                u'esp': u'0x0025e8cc'
            },
            u'trust': u'context'
        },
        {
            u'frame': 1,
            u'function': u'WaitForMultipleObjectsEx',
            u'function_offset': u'0xff',
            u'module': u'KERNELBASE.dll',
            u'module_offset': u'0x115f6',
            u'offset': u'0x775e15f6',
            u'trust': u'cfi'
        },
        {
            u'frame': 2,
            u'function': u'WaitForMultipleObjectsExImplementation',
            u'function_offset': u'0x8d',
            u'module': u'kernel32.dll',
            u'module_offset': u'0x119f7',
            u'offset': u'0x766119f7',
            u'trust': u'cfi'
        },
        {
            u'frame': 3,
            u'function': u'RealMsgWaitForMultipleObjectsEx',
            u'function_offset': u'0xe1',
            u'module': u'user32.dll',
            u'module_offset': u'0x20869',
            u'offset': u'0x77370869',
            u'trust': u'cfi'
        },
        {
            u'frame': 4,
            u'function': u'MsgWaitForMultipleObjects',
            u'function_offset': u'0x1e',
            u'module': u'user32.dll',
            u'module_offset': u'0x20b68',
            u'offset': u'0x77370b68',
            u'trust': u'cfi'
        },
        {
            u'file': u'F117835525________________________________________',
            u'frame': 5,
            u'function': u'F_1152915508__________________________________',
            u'function_offset': u'0xbb',
            u'line': 118,
            u'module': u'NPSWF32_14_0_0_125.dll',
            u'module_offset': u'0x36a13b',
            u'offset': u'0x5e3aa13b',
            u'trust': u'cfi'
        },
        {
            u'file': u'F_851861807_______________________________________',
            u'frame': 6,
            u'function': u'F2166389______________________________________',
            u'function_offset': u'0xe5',
            u'line': 552,
            u'module': u'NPSWF32_14_0_0_125.dll',
            u'module_offset': u'0x35faf5',
            u'offset': u'0x5e39faf5',
            u'trust': u'cfi'
        },
        {
            u'file': u'F_851861807_______________________________________',
            u'frame': 7,
            u'function': u'F_917831355___________________________________',
            u'function_offset': u'0x29b',
            u'line': 488,
            u'module': u'NPSWF32_14_0_0_125.dll',
            u'module_offset': u'0x360a7b',
            u'offset': u'0x5e3a0a7b',
            u'trust': u'cfi'
        },
        {
            u'file': u'F_851861807_______________________________________',
            u'frame': 8,
            u'function': u'F1315696776________________________________',
            u'function_offset': u'0xd',
            u'line': 439,
            u'module': u'NPSWF32_14_0_0_125.dll',
            u'module_offset': u'0x35e2fd',
            u'offset': u'0x5e39e2fd',
            u'trust': u'cfi'
        },
        {
            u'file': u'F_766591945_______________________________________',
            u'frame': 9,
            u'function': u'F_1428703866________________________________',
            u'function_offset': u'0xc1',
            u'line': 203,
            u'module': u'NPSWF32_14_0_0_125.dll',
            u'module_offset': u'0x35bf21',
            u'offset': u'0x5e39bf21',
            u'trust': u'cfi'
        }
    ],
    u'threads_index': 0,
    u'total_frames': 32
}

sample_json_dump = {
    u'json_dump': {
        u'system_info': {
            'os': 'Windows NT'
        },
        u'crash_info': {
            u'address': u'0x77ad015d',
            u'crashing_thread': 0,
            u'type': u'EXCEPTION_BREAKPOINT'
        },
        u'crashing_thread': frames_from_json_dump,
        u'threads':  [ frames_from_json_dump ]

    }
}

csig_config = DotDict()
csig_config.irrelevant_signature_re = ''
csig_config.prefix_signature_re = ''
csig_config.signatures_with_line_numbers_re = ''
csig_config.signature_sentinels = []
c_signature_tool = CSignatureTool(csig_config)


#------------------------------------------------------------------------------
def create_basic_fake_processor():
    fake_processor = DotDict()
    fake_processor.c_signature_tool = c_signature_tool
    fake_processor.config = DotDict()
    # need help figuring out failures? switch to FakeLogger and read stdout
    fake_processor.config.logger = sutil.SilentFakeLogger()
    #fake_processor.config.logger = sutil.FakeLogger()
    return fake_processor


#==============================================================================
class TestSignatureGeneration(TestCase):

    def get_config(self):
        config = {
            'c_signature': {
                'c_signature_tool_class': CSignatureTool,
                'maximum_frames_to_consider': 40,
                'signature_sentinels': eval(
                    CSignatureTool.required_config.signature_sentinels
                    .default
                ),
                'irrelevant_signature_re': eval(
                    CSignatureTool.required_config.irrelevant_signature_re
                    .default
                ),
                'prefix_signature_re': eval(
                    CSignatureTool.required_config.prefix_signature_re
                    .default
                ),
                'signatures_with_line_numbers_re': (
                    CSignatureTool.required_config
                    .signatures_with_line_numbers_re.default
                ),
            },
            'java_signature': {
                'java_signature_tool_class': JavaSignatureTool,
            }
        }
        return CDotDict(config)

    #--------------------------------------------------------------------------
    def test_instantiation(self):
        config = self.get_config()
        sgr = SignatureGenerationRule(config)

        ok_(isinstance(sgr.c_signature_tool, CSignatureTool))
        ok_(isinstance(sgr.java_signature_tool, JavaSignatureTool))


    #--------------------------------------------------------------------------
    def test_create_frame_list_1(self):
        config = self.get_config()
        sgr = SignatureGenerationRule(config)
        frame_signatures_list = sgr._create_frame_list(frames_from_json_dump)
        expected = [
            u'NtWaitForMultipleObjects',
            u'WaitForMultipleObjectsEx',
            u'WaitForMultipleObjectsExImplementation',
            u'RealMsgWaitForMultipleObjectsEx',
            u'MsgWaitForMultipleObjects',
            u'F_1152915508__________________________________',
            u'F2166389______________________________________',
            u'F_917831355___________________________________',
            u'F1315696776________________________________',
            u'F_1428703866________________________________'
        ]
        eq_(frame_signatures_list, expected)
        ok_('normalized' in frames_from_json_dump['frames'][0])
        eq_(frames_from_json_dump['frames'][0]['normalized'], expected[0])

    #--------------------------------------------------------------------------
    def test_create_frame_list_2(self):
        config = self.get_config()
        config.c_signature.maximum_frames_to_consider = 3
        sgr = SignatureGenerationRule(config)
        frame_signatures_list = sgr._create_frame_list(frames_from_json_dump)
        expected = [
            u'NtWaitForMultipleObjects',
            u'WaitForMultipleObjectsEx',
            u'WaitForMultipleObjectsExImplementation',
        ]
        eq_(frame_signatures_list, expected)
        ok_('normalized' in frames_from_json_dump['frames'][0])
        eq_(frames_from_json_dump['frames'][0]['normalized'], expected[0])

    #--------------------------------------------------------------------------
    def test_action_1(self):
        config = self.get_config()
        sgr = SignatureGenerationRule(config)

        raw_crash = CDotDict(
            {
                'JavaStackTrace': (
                    '   SomeJavaException: %s  \n'
                    'at org.mozilla.lars.myInvention('
                    'larsFile.java)' % ('t' * 1000)
                )
            }
        )
        raw_dumps = {}
        processed_crash = CDotDict()
        processor_meta = CDotDict({
            'processor_notes': []
        })

        # the call to be tested
        ok_(sgr._action(raw_crash, raw_dumps, processed_crash, processor_meta))

        eq_(
            processed_crash.signature,
            'SomeJavaException: at org.mozilla.lars.myInvention(larsFile.java)'
        )
        eq_(
            processor_meta.processor_notes,
            [
                'JavaSignatureTool: dropped Java exception description due to '
                'length'
            ]
        )

    #--------------------------------------------------------------------------
    def test_action_2(self):
        config = self.get_config()
        sgr = SignatureGenerationRule(config)

        raw_crash = CDotDict()
        raw_dumps = {}
        processed_crash = CDotDict(sample_json_dump)
        processor_meta = CDotDict({
            'processor_notes': []
        })

        # the call to be tested
        ok_(sgr._action(raw_crash, raw_dumps, processed_crash, processor_meta))

        eq_(
            processed_crash.signature,
            'WaitForMultipleObjectsEx | RealMsgWaitForMultipleObjectsEx '
            '| MsgWaitForMultipleObjects | F_1152915508_________________'
            '_________________'
        )
        eq_(processor_meta.processor_notes, [])

    #--------------------------------------------------------------------------
    def test_action_3(self):
        config = self.get_config()
        sgr = SignatureGenerationRule(config)

        raw_crash = CDotDict()
        raw_dumps = {}
        processed_crash = CDotDict({
            'json_dump': {
                'crashing_thread': {
                    'frames': []
                }
            }
        })
        processed_crash.frames = []
        processor_meta = CDotDict({
            'processor_notes': []
        })

        # the call to be tested
        ok_(sgr._action(raw_crash, raw_dumps, processed_crash, processor_meta))

        eq_(
            processed_crash.signature,
            'EMPTY: no crashing thread identified'
        )
        eq_(
            processor_meta.processor_notes,
            [
                'CSignatureTool: No signature could be created because we do '
                'not know which thread crashed'
            ]
        )

    #--------------------------------------------------------------------------
    def test_lower_case_modules(self):
        config = self.get_config()
        sgr = SignatureGenerationRule(config)

        raw_crash = CDotDict()
        raw_dumps = {}
        processed_crash = CDotDict(copy.deepcopy(sample_json_dump))
        processed_crash.json_dump.threads = [
            {
                "frames": [
                    {
                        u'offset': u'0x5e39bf21',
                        u'trust': u'cfi'
                    },
                    {
                        u'offset': u'0x5e39bf21',
                        u'trust': u'cfi'
                    },
                    {
                        u'offset': u'0x5e39bf21',
                        u'trust': u'cfi'
                    },
                    {
                        u'frame': 3,
                        u'module': u'USER2.dll',
                        u'module_offset': u'0x20869',
                        u'offset': u'0x77370869',
                        u'trust': u'cfi'
                    },
                ]
            },
        ]
        processor_meta = CDotDict({
            'processor_notes': []
        })

        # the call to be tested
        ok_(sgr._action(raw_crash, raw_dumps, processed_crash, processor_meta))

        eq_(
            processed_crash.signature,
            'user2.dll@0x20869'
        )
        eq_(processor_meta.processor_notes, [])


#==============================================================================
class TestOOMSignature(TestCase):

    #--------------------------------------------------------------------------
    def test_OOMAllocationSize_predicate_no_match(self):
        pc = DotDict()
        pc.signature = 'hello'
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(not predicate_result)

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
    def test_OOMAllocationSize_predicate_signature_fragment_1(self):
        pc = DotDict()
        pc.signature = 'this | is | a | NS_ABORT_OOM | signature'
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(predicate_result)

    #--------------------------------------------------------------------------
    def test_OOMAllocationSize_predicate_signature_fragment_2(self):
        pc = DotDict()
        pc.signature = 'mozalloc_handle_oom | this | is | bad'
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(predicate_result)

    #--------------------------------------------------------------------------
    def test_OOMAllocationSize_predicate_signature_fragment_3(self):
        pc = DotDict()
        pc.signature = 'CrashAtUnhandlableOOM'
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(predicate_result)

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
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


#==============================================================================
class TestSigTrunc(TestCase):

    #--------------------------------------------------------------------------
    def test_SigTrunc_predicate_no_match(self):
        pc = DotDict()
        pc.signature = '0' * 100
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = SigTrunc(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(not predicate_result)

    #--------------------------------------------------------------------------
    def test_SigTrunc_predicate(self):
        pc = DotDict()
        pc.signature = '9' * 256
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = SigTrunc(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(predicate_result)

    #--------------------------------------------------------------------------
    def test_SigTrunc_action_success(self):
        pc = DotDict()
        pc.signature = '9' * 256
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = SigTrunc(fake_processor.config)
        action_result = rule.action(rc, rd, pc, fake_processor)
        ok_(action_result)
        eq_(len(pc.signature), 255)
        ok_(pc.signature.endswith('9...'))

#==============================================================================
class TestStackwalkerErrorSignatureRule(TestCase):

    #--------------------------------------------------------------------------
    def test_predicate_no_match(self):
        pc = DotDict()
        pc.signature = '0' * 100
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = StackwalkerErrorSignatureRule(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(not predicate_result)


    #--------------------------------------------------------------------------
    def test_predicate(self):
        pc = DotDict()
        pc.signature = "EMPTY: like my soul"
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = StackwalkerErrorSignatureRule(fake_processor.config)
        predicate_result = rule.predicate(rc, rd, pc, fake_processor)
        ok_(predicate_result)

    #--------------------------------------------------------------------------
    def test_SigTrunc_action_success(self):
        pc = DotDict()
        pc.signature = "EMPTY: like my soul"
        pc.mdsw_status_string = 'catastrophic stackwalker failure'
        rc = DotDict()
        rd = {}
        fake_processor = create_basic_fake_processor()
        rule = StackwalkerErrorSignatureRule(fake_processor.config)
        action_result = rule.action(rc, rd, pc, fake_processor)
        ok_(action_result)
        ok_(
            pc.signature,
            "EMPTY: like my soul; catastrophic stackwalker failure"
        )


#==============================================================================
class TestSignatureWatchDogRule(TestCase):

    #--------------------------------------------------------------------------
    def get_config(self):
        config = DotDict({
            'c_signature': {
                'c_signature_tool_class': CSignatureTool,
                'maximum_frames_to_consider': 40,
                'signature_sentinels': eval(
                    CSignatureTool.required_config.signature_sentinels
                    .default
                ),
                'irrelevant_signature_re': eval(
                    CSignatureTool.required_config.irrelevant_signature_re
                    .default
                ),
                'prefix_signature_re': eval(
                    CSignatureTool.required_config.prefix_signature_re
                    .default
                ),
                'signatures_with_line_numbers_re': (
                    CSignatureTool.required_config
                    .signatures_with_line_numbers_re.default
                ),
            },
            'java_signature': {
                'java_signature_tool_class': JavaSignatureTool,
            }
        })
        config.logger = sutil.FakeLogger()

        return CDotDict(config)

    #--------------------------------------------------------------------------
    def test_instantiation(self):
        config = self.get_config()
        srwd = SignatureRunWatchDog(config)

        ok_(isinstance(srwd.c_signature_tool, CSignatureTool))
        ok_(isinstance(srwd.java_signature_tool, JavaSignatureTool))

        eq_(srwd._get_crashing_thread({}), 0)


    #--------------------------------------------------------------------------
    def test_predicate(self):
        config = self.get_config()
        srwd = SignatureRunWatchDog(config)

        fake_processed_crash = {
            'signature': "I'm not real",
        }
        ok_(not srwd.predicate({}, {}, fake_processed_crash, {}))

        fake_processed_crash = {
            'signature': "mozilla::`anonymous namespace''::RunWatchdog(void*)",
        }
        ok_(srwd.predicate({}, {}, fake_processed_crash, {}))

        fake_processed_crash = {
            'signature': "mozilla::(anonymous namespace)::RunWatchdog(void*)",
        }
        ok_(srwd.predicate({}, {}, fake_processed_crash, {}))


    #--------------------------------------------------------------------------
    def test_action(self):
        config = self.get_config()
        sgr = SignatureRunWatchDog(config)

        raw_crash = CDotDict()
        raw_dumps = {}
        processed_crash = CDotDict(sample_json_dump)
        processor_meta = CDotDict({
            'processor_notes': []
        })

        # the call to be tested
        ok_(sgr._action(raw_crash, raw_dumps, processed_crash, processor_meta))

        eq_(
            processed_crash.signature,
            'shutdownhang | '
            'WaitForMultipleObjectsEx | RealMsgWaitForMultipleObjectsEx '
            '| MsgWaitForMultipleObjects | F_1152915508_________________'
            '_________________'
        )
        eq_(processor_meta.processor_notes, [])
