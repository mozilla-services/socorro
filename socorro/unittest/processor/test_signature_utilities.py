# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import copy
import json
import mock
import re

from configman.dotdict import DotDict as CDotDict

import socorro.lib.util as sutil

from socorro.lib.util import DotDict
from socorro.processor.signature_utilities import (
    AbortSignature,
    CSignatureTool,
    JavaSignatureTool,
    OOMSignature,
    StackwalkerErrorSignatureRule,
    SignatureIPCChannelError,
    SignatureGenerationRule,
    SignatureJitCategory,
    SignatureRunWatchDog,
    SigTrim,
    SigTrunc,
    SignatureShutdownTimeout,
    SignatureIPCMessageName,
)
from socorro.unittest.processor import create_basic_fake_processor
from socorro.unittest.testbase import TestCase


class TestCSignatureTool(TestCase):

    @staticmethod
    def setup_config_c_sig_tool(
        ig=['ignored1'],
        pr=['pre1', 'pre2'],
        si=['fnNeedNumber'],
        td=['foo32\.dll.*'],
        ss=('sentinel', ('sentinel2', lambda x: 'ff' in x)),
    ):
        config = sutil.DotDict()
        config.logger = sutil.FakeLogger()
        config.collapse_arguments = True

        with mock.patch(
            'socorro.processor.signature_utilities.siglists'
        ) as mocked_siglists:
            mocked_siglists.IRRELEVANT_SIGNATURE_RE = ig
            mocked_siglists.PREFIX_SIGNATURE_RE = pr
            mocked_siglists.SIGNATURES_WITH_LINE_NUMBERS_RE = si
            mocked_siglists.TRIM_DLL_SIGNATURE_RE = td
            mocked_siglists.SIGNATURE_SENTINELS = ss
            s = CSignatureTool(config)

        return s, config

    def test_c_config_tool_init(self):
        """test_C_config_tool_init: constructor test"""
        expected_regex = sutil.DotDict()
        expected_regex.irrelevant_signature_re = re.compile('ignored1')
        expected_regex.prefix_signature_re = re.compile('pre1|pre2')
        expected_regex.signatures_with_line_numbers_re = re.compile(
            'fnNeedNumber'
        )
        fixup_space = re.compile(r' (?=[\*&,])')
        fixup_comma = re.compile(r',(?! )')

        s, c = self.setup_config_c_sig_tool()

        assert c == s.config
        assert expected_regex.irrelevant_signature_re == s.irrelevant_signature_re
        assert expected_regex.prefix_signature_re == s.prefix_signature_re
        assert expected_regex.signatures_with_line_numbers_re == s.signatures_with_line_numbers_re
        assert fixup_space.pattern == s.fixup_space.pattern
        assert fixup_comma.pattern == s.fixup_comma.pattern

    def test_normalize_with_collapse_args(self):
        """test_normalize: bunch of variations"""
        s, c = self.setup_config_c_sig_tool()
        a = [
            (('module', 'fn', 'source', '23', '0xFFF'), 'fn'),
            (('module', 'fnNeedNumber', 's', '23', '0xFFF'),
             'fnNeedNumber:23'),
            (('module', 'f( *s)', 's', '23', '0xFFF'), 'f'),
            (('module', 'f( &s)', 's', '23', '0xFFF'), 'f'),
            (('module', 'f( *s , &n)', 's', '23', '0xFFF'), 'f'),
            # this next one looks like a bug to me, but perhaps the situation
            # never comes up
            #(('module', 'f(  *s , &n)', 's', '23', '0xFFF'), 'f(*s, &n)'),
            (('module', 'f3(s,t,u)', 's', '23', '0xFFF'), 'f3'),
            (
                (
                    'module',
                    '::(anonymous namespace)::f3(s,t,u)',
                    's',
                    '23',
                    '0xFFF'
                ),
                '::(anonymous namespace)::f3'
            ),
            (
                (
                    'module',
                    'operator()(s,t,u)',
                    's',
                    '23',
                    '0xFFF'
                ),
                'operator()'
            ),
            (
                (
                    'module',
                    'Alpha<Bravo<Charlie>, Delta>::Echo<Foxtrot>',
                    's',
                    '23',
                    '0xFFF'
                ),
                'Alpha<T>::Echo<T>'
            ),
            (('module', 'f<3>(s,t,u)', 's', '23', '0xFFF'), 'f<T>'),
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
            assert e == r

    def test_generate_1(self):
        """test_generate_1: simple"""
        s, c = self.setup_config_c_sig_tool(['a', 'b', 'c'], ['d', 'e', 'f'])
        a = list('abcdefghijklmnopqrstuvwxyz')
        sig, notes = s.generate(a)
        assert sig == 'd | e | f | g'

        a = list('abcdaeafagahijklmnopqrstuvwxyz')
        sig, notes = s.generate(a)
        assert sig == 'd | e | f | g'

    def test_generate_2(self):
        """test_generate_2: hang"""
        s, c = self.setup_config_c_sig_tool(['a', 'b', 'c'], ['d', 'e', 'f'])
        a = list('abcdefghijklmnopqrstuvwxyz')
        sig, notes = s.generate(a, hang_type=-1)
        assert sig == 'hang | d | e | f | g'

        a = list('abcdaeafagahijklmnopqrstuvwxyz')
        sig, notes = s.generate(a, hang_type=-1)
        assert sig == 'hang | d | e | f | g'

        a = list('abcdaeafagahijklmnopqrstuvwxyz')
        sig, notes = s.generate(a, hang_type=0)
        assert sig == 'd | e | f | g'

        a = list('abcdaeafagahijklmnopqrstuvwxyz')
        sig, notes = s.generate(a, hang_type=1)
        assert sig == 'chromehang | d | e | f | g'

    def test_generate_2a(self):
        """test_generate_2a: way too long"""
        s, c = self.setup_config_c_sig_tool(['a', 'b', 'c'], ['d', 'e', 'f'])
        a = list('abcdefghijklmnopqrstuvwxyz')
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
        assert sig == e
        e = "hang | ddddddddddddddddddddddddddddddddddddddddddddddddddd" \
            "ddddddddddddddddddd " \
            "| eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee" \
            "eeeeeeeeeeeeee " \
            "| ffffffffffffffffffffffffffffffffffffffffffffffffffffffff" \
            "ffffffffffffff | gggggggggggggggggggggggggg..."
        sig, notes = s.generate(a, hang_type=-1)
        assert sig == e

    def test_generate_3(self):
        """test_generate_3: simple sentinel"""
        s, c = self.setup_config_c_sig_tool(['a', 'b', 'c'], ['d', 'e', 'f'])
        a = list('abcdefghabcfaeabdijklmnopqrstuvwxyz')
        a[7] = 'sentinel'
        sig, notes = s.generate(a)
        assert sig == 'sentinel'

        s, c = self.setup_config_c_sig_tool(
            ['a', 'b', 'c', 'sentinel'],
            ['d', 'e', 'f']
        )
        sig, notes = s.generate(a)
        assert sig == 'f | e | d | i'

    def test_generate_4(self):
        """test_generate_4: tuple sentinel"""
        s, c = self.setup_config_c_sig_tool(['a', 'b', 'c'], ['d', 'e', 'f'])
        a = list('abcdefghabcfaeabdijklmnopqrstuvwxyz')
        a[7] = 'sentinel2'
        sig, notes = s.generate(a)
        assert sig == 'd | e | f | g'

        s, c = self.setup_config_c_sig_tool(['a', 'b', 'c'], ['d', 'e', 'f'])
        a = list('abcdefghabcfaeabdijklmnopqrstuvwxyz')
        a[7] = 'sentinel2'
        a[22] = 'ff'
        sig, notes = s.generate(a)
        assert sig == 'sentinel2'

        s, c = self.setup_config_c_sig_tool(
            ['a', 'b', 'c', 'sentinel2'],
            ['d', 'e', 'f']
        )
        a = list('abcdefghabcfaeabdijklmnopqrstuvwxyz')
        a[7] = 'sentinel2'
        a[22] = 'ff'
        sig, notes = s.generate(a)
        assert sig == 'f | e | d | i'

    def test_generate_with_merged_dll(self):
        generator, config = self.setup_config_c_sig_tool(
            ['a', 'b', 'c'],
            ['d', 'e', 'f']
        )
        source_list = (
            'a',
            'd',
            'foo32.dll@0x231423',
            'foo32.dll',
            'foo32.dll@0x42',
            'g',
        )
        sig, notes = generator.generate(source_list)
        assert sig == 'd | foo32.dll | g'

        source_list = (
            'foo32.dll',
            'foo32.dll@0x231423',
            'g',
        )
        sig, notes = generator.generate(source_list)
        assert sig == 'foo32.dll | g'


class TestJavaSignatureTool(TestCase):
    def test_generate_signature_1(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 17
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = "EMPTY: Java stack trace not in expected format"
        assert sig == e
        e = ['JavaSignatureTool: stack trace not '
             'in expected format']
        assert notes == e

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
        assert sig == e
        assert notes == []

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
        assert sig == e
        assert notes == []

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
        assert sig == e
        e = ['JavaSignatureTool: dropped Java exception description due to '
             'length']
        assert notes == e

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
        assert sig == e
        e = ['JavaSignatureTool: dropped Java exception description due to '
             'length']
        assert notes == e

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
        assert sig == e
        e = ['JavaSignatureTool: stack trace line 1 is '
             'not in the expected format']
        assert notes == e

    def test_generate_signature_6(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 'SomeJavaException: totally made up  \n'
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = 'SomeJavaException: totally made up'
        assert sig == e
        e = ['JavaSignatureTool: stack trace line 2 is missing']
        assert notes == e

    def test_generate_signature_7(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 'SomeJavaException: totally made up  '
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = 'SomeJavaException: totally made up'
        assert sig == e
        e = ['JavaSignatureTool: stack trace line 2 is missing']
        assert notes == e

    def test_generate_signature_8(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 'SomeJavaException: totally made up  '
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = 'SomeJavaException: totally made up'
        assert sig == e
        e = ['JavaSignatureTool: stack trace line 2 is missing']
        assert notes == e

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
        assert sig == e
        e = ['JavaSignatureTool: dropped Java exception description due to '
             'length',
             'SignatureTool: signature truncated due to length']
        assert notes == e

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
        assert sig == e
        assert notes == []

    def test_generate_signature_11_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """
java.lang.IllegalArgumentException: Given view not a child of android.widget.AbsoluteLayout@4054b560
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
\tat dalvik.system.NativeStart.main(Native Method)""".lstrip()
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('java.lang.IllegalArgumentException: '
             'Given view not a child of android.widget.AbsoluteLayout@<addr>: '
             'at android.view.ViewGroup.updateViewLayout(ViewGroup.java)')
        assert sig == e
        assert notes == []

    def test_generate_signature_12_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """
java.lang.IllegalArgumentException: Given view not a child of android.widget.AbsoluteLayout@4054b560
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
\tat dalvik.system.NativeStart.main(Native Method)""".lstrip()
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('java.lang.IllegalArgumentException: '
             'Given view not a child of android.widget.AbsoluteLayout@<addr>: '
             'at android.view.ViewGroup.updateViewLayout(ViewGroup.java)')
        assert sig == e
        assert notes == []

    def test_generate_signature_13_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """
java.lang.IllegalArgumentException: Receiver not registered: org.mozilla.gecko.GeckoConnectivityReceiver@2c004bc8
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
\tat dalvik.system.NativeStart.main(Native Method)""".lstrip()  # noqa
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('java.lang.IllegalArgumentException: '
             'Receiver not registered: '
             'org.mozilla.gecko.GeckoConnectivityReceiver@<addr>: '
             'at android.app.LoadedApk.forgetReceiverDispatcher'
             '(LoadedApk.java)')
        assert sig == e
        assert notes == []

    def test_generate_signature_14_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """
android.view.WindowManager$BadTokenException: Unable to add window -- token android.os.BinderProxy@406237c0 is not valid; is your activity running?
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
""".lstrip()  # noqa
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = ('android.view.WindowManager$BadTokenException: '
             'Unable to add window -- token android.os.BinderProxy@<addr> '
             'is not valid; is your activity running? '
             'at android.view.ViewRoot.setView(ViewRoot.java)')
        assert sig == e
        assert notes == []

    def test_generate_signature_15_replace_address(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = """
java.lang.IllegalArgumentException: Receiver not registered: org.mozilla.gecko.GeckoNetworkManager@405afea8
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
""".lstrip()  # noqa
        sig, notes = j.generate(java_stack_trace, delimiter=': ')
        e = (
            'java.lang.IllegalArgumentException: '
            'Receiver not registered: '
            'org.mozilla.gecko.GeckoNetworkManager@<addr>: '
            'at android.app.LoadedApk.forgetReceiverDispatcher(LoadedApk.java)'
        )
        assert sig == e
        assert notes == []


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

frames_from_json_dump_with_templates = {
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
            u'function': u'Alpha<Bravo<Charlie>, Delta>::Echo<Foxtrot>',
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
            u'function': u'RealMsgWaitForMultipleObjectsEx(void **fakeargs)',
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

frames_from_json_dump_with_templates_and_special_case = {
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
            u'function': u'<name omitted>',
            u'function_offset': u'0xff',
            u'module': u'KERNELBASE.dll',
            u'module_offset': u'0x115f6',
            u'offset': u'0x775e15f6',
            u'trust': u'cfi'
        },
        {
            u'frame': 2,
            u'function': u'IPC::ParamTraits<mozilla::net::NetAddr>::Write',
            u'function_offset': u'0x8d',
            u'module': u'kernel32.dll',
            u'module_offset': u'0x119f7',
            u'offset': u'0x766119f7',
            u'trust': u'cfi'
        },
        {
            u'frame': 3,
            u'function': u'RealMsgWaitForMultipleObjectsEx(void **fakeargs)',
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
        u'threads': [frames_from_json_dump]

    }
}

sample_json_dump_with_templates = {
    u'json_dump': {
        u'system_info': {
            'os': 'Windows NT'
        },
        u'crash_info': {
            u'address': u'0x77ad015d',
            u'crashing_thread': 0,
            u'type': u'EXCEPTION_BREAKPOINT'
        },
        u'crashing_thread': frames_from_json_dump_with_templates,
        u'threads': [frames_from_json_dump_with_templates]

    }
}

sample_json_dump_with_templates_and_special_case = {
    u'json_dump': {
        u'system_info': {
            'os': 'Windows NT'
        },
        u'crash_info': {
            u'address': u'0x77ad015d',
            u'crashing_thread': 0,
            u'type': u'EXCEPTION_BREAKPOINT'
        },
        u'crashing_thread':
            frames_from_json_dump_with_templates_and_special_case,
        u'threads': [frames_from_json_dump_with_templates_and_special_case]

    }
}

class TestSignatureGeneration(TestCase):

    def get_config(self):
        config = {
            'c_signature': {
                'c_signature_tool_class': CSignatureTool,
                'maximum_frames_to_consider': 40,
                'collapse_arguments': True,
            },
            'java_signature': {
                'java_signature_tool_class': JavaSignatureTool,
            }
        }
        return CDotDict(config)

    def test_instantiation(self):
        config = self.get_config()
        sgr = SignatureGenerationRule(config)

        assert isinstance(sgr.c_signature_tool, CSignatureTool)
        assert isinstance(sgr.java_signature_tool, JavaSignatureTool)

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
        assert frame_signatures_list == expected
        assert 'normalized' in frames_from_json_dump['frames'][0]
        assert frames_from_json_dump['frames'][0]['normalized'] == expected[0]

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
        assert frame_signatures_list == expected
        assert 'normalized' in frames_from_json_dump['frames'][0]
        assert frames_from_json_dump['frames'][0]['normalized'] == expected[0]

    def test_action_1(self):
        config = self.get_config()
        sgr = SignatureGenerationRule(config)

        raw_crash = {
            'JavaStackTrace': (
                '   SomeJavaException: %s  \n'
                'at org.mozilla.lars.myInvention('
                'larsFile.java)' % ('t' * 1000)
            )
        }

        processed_crash = {}
        processor_meta = {
            'processor_notes': []
        }

        # the call to be tested
        assert sgr._action(raw_crash, {}, processed_crash, processor_meta) is True

        assert (
            processed_crash['signature'] ==
            'SomeJavaException: at org.mozilla.lars.myInvention(larsFile.java)'
        )
        assert (
            processor_meta['processor_notes'] ==
            [
                'JavaSignatureTool: dropped Java exception description due to '
                'length'
            ]
        )
        assert 'proto_signature' not in processed_crash

    def test_action_2(self):
        config = self.get_config()
        sgr = SignatureGenerationRule(config)

        raw_crash = {}
        processed_crash = dict(sample_json_dump)
        processor_meta = {
            'processor_notes': []
        }

        # the call to be tested
        assert sgr._action(raw_crash, {}, processed_crash, processor_meta) is True

        expected = 'MsgWaitForMultipleObjects | F_1152915508__________________________________'
        assert processed_crash['signature'] == expected
        expected = (
            'NtWaitForMultipleObjects | WaitForMultipleObjectsEx | '
            'WaitForMultipleObjectsExImplementation | '
            'RealMsgWaitForMultipleObjectsEx | MsgWaitForMultipleObjects | '
            'F_1152915508__________________________________ | '
            'F2166389______________________________________ | '
            'F_917831355___________________________________ | '
            'F1315696776________________________________ | '
            'F_1428703866________________________________'
        )
        assert processed_crash['proto_signature'] == expected
        assert processor_meta['processor_notes'] == []

    def test_action_2_with_templates(self):
        config = self.get_config()
        sgr = SignatureGenerationRule(config)

        raw_crash = {}
        processed_crash = dict(sample_json_dump_with_templates)
        processor_meta = {
            'processor_notes': []
        }

        # the call to be tested
        assert sgr._action(raw_crash, {}, processed_crash, processor_meta) is True

        assert processed_crash['signature'] == 'Alpha<T>::Echo<T>'
        expected = (
            'NtWaitForMultipleObjects | Alpha<T>::Echo<T> | '
            'WaitForMultipleObjectsExImplementation | '
            'RealMsgWaitForMultipleObjectsEx | '
            'MsgWaitForMultipleObjects | '
            'F_1152915508__________________________________ | '
            'F2166389______________________________________ | '
            'F_917831355___________________________________ | '
            'F1315696776________________________________ | '
            'F_1428703866________________________________'
        )
        assert processed_crash['proto_signature'] == expected
        assert processor_meta['processor_notes'] == []

    def test_action_2_with_templates_and_special_case(self):
        config = self.get_config()
        sgr = SignatureGenerationRule(config)

        raw_crash = {}
        processed_crash = dict(sample_json_dump_with_templates_and_special_case)
        processor_meta = {
            'processor_notes': []
        }

        # the call to be tested
        assert sgr._action(raw_crash, {}, processed_crash, processor_meta) is True

        expected = '<name omitted> | IPC::ParamTraits<mozilla::net::NetAddr>::Write'
        assert processed_crash['signature'] == expected
        expected = (
            'NtWaitForMultipleObjects | '
            '<name omitted> | '
            'IPC::ParamTraits<mozilla::net::NetAddr>::Write | '
            'RealMsgWaitForMultipleObjectsEx | '
            'MsgWaitForMultipleObjects | '
            'F_1152915508__________________________________ | '
            'F2166389______________________________________ | '
            'F_917831355___________________________________ | '
            'F1315696776________________________________ | '
            'F_1428703866________________________________'
        )
        assert processed_crash['proto_signature'] == expected
        assert processor_meta['processor_notes'] == []

    def test_action_3(self):
        config = self.get_config()
        sgr = SignatureGenerationRule(config)

        raw_crash = {}
        processed_crash = {
            'json_dump': {
                'crashing_thread': {
                    'frames': []
                }
            }
        }
        processed_crash['frames'] = []
        processor_meta = {
            'processor_notes': []
        }

        # the call to be tested
        assert sgr._action(raw_crash, {}, processed_crash, processor_meta) is True

        assert processed_crash['signature'] == 'EMPTY: no crashing thread identified'
        assert processed_crash['proto_signature'] == ''
        expected = [
            'CSignatureTool: No signature could be created because we do '
            'not know which thread crashed'
        ]
        assert processor_meta['processor_notes'] == expected

    def test_lower_case_modules(self):
        config = self.get_config()
        sgr = SignatureGenerationRule(config)

        raw_crash = {}
        processed_crash = copy.deepcopy(sample_json_dump)
        processed_crash['json_dump']['threads'] = [
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
        processor_meta = {
            'processor_notes': []
        }

        # the call to be tested
        assert sgr._action(raw_crash, {}, processed_crash, processor_meta) is True

        assert processed_crash['signature'] == 'user2.dll@0x20869'
        expected = '@0x5e39bf21 | @0x5e39bf21 | @0x5e39bf21 | user2.dll@0x20869'
        assert processed_crash['proto_signature'] == expected
        assert processor_meta['processor_notes'] == []


class TestOOMSignature(TestCase):

    def test_predicate_no_match(self):
        processed_crash = {
            'signature': 'hello'
        }
        raw_crash = {}
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(raw_crash, {}, processed_crash, fake_processor)
        assert predicate_result is False

    def test_predicate(self):
        processed_crash = {
            'signature': 'hello'
        }
        raw_crash = {
            'OOMAllocationSize': 17
        }
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(raw_crash, {}, processed_crash, fake_processor)
        assert predicate_result is True

    def test_predicate_signature_fragment_1(self):
        processed_crash = {
            'signature': 'this | is | a | NS_ABORT_OOM | signature'
        }
        raw_crash = {}
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(raw_crash, {}, processed_crash, fake_processor)
        assert predicate_result is True

    def test_predicate_signature_fragment_2(self):
        processed_crash = {
            'signature': 'mozalloc_handle_oom | this | is | bad'
        }
        raw_crash = {}
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(raw_crash, {}, processed_crash, fake_processor)
        assert predicate_result is True

    def test_predicate_signature_fragment_3(self):
        processed_crash = {
            'signature': 'CrashAtUnhandlableOOM'
        }
        raw_crash = {}
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        predicate_result = rule.predicate(raw_crash, {}, processed_crash, fake_processor)
        assert predicate_result is True

    def test_action_success(self):
        processed_crash = {
            'signature': 'hello'
        }
        raw_crash = {}
        fake_processor = create_basic_fake_processor()
        rule = OOMSignature(fake_processor.config)
        action_result = rule.action(raw_crash, {}, processed_crash, fake_processor)

        assert action_result is True
        assert processed_crash['original_signature'] == 'hello'
        assert processed_crash['signature'] == 'OOM | unknown | hello'

    def test_action_small(self):
        processed_crash = {
            'signature': 'hello'
        }
        raw_crash = {
            'OOMAllocationSize': 17
        }
        fake_processor = create_basic_fake_processor()

        rule = OOMSignature(fake_processor.config)
        action_result = rule.action(raw_crash, {}, processed_crash, fake_processor)

        assert action_result is True
        assert processed_crash['original_signature'] == 'hello'
        assert processed_crash['signature'] == 'OOM | small'

    def test_action_large(self):
        processed_crash = {
            'signature': 'hello'
        }
        raw_crash = {
            'OOMAllocationSize': 17000000
        }
        fake_processor = create_basic_fake_processor()

        rule = OOMSignature(fake_processor.config)
        action_result = rule.action(raw_crash, {}, processed_crash, fake_processor)

        assert action_result is True
        assert processed_crash['original_signature'] == 'hello'
        assert processed_crash['signature'] == 'OOM | large | hello'


class TestAbortSignature(TestCase):

    def get_config(self):
        fake_processor = create_basic_fake_processor()
        return fake_processor.config

    def test_predicate(self):
        config = self.get_config()
        rule = AbortSignature(config)

        processed_crash = {
            'signature': 'hello'
        }
        raw_crash = {
            'AbortMessage': 'something'
        }

        predicate_result = rule.predicate(raw_crash, {}, processed_crash, {})
        assert predicate_result is True

    def test_predicate_no_match(self):
        config = self.get_config()
        rule = AbortSignature(config)
        processed_crash = {
            'signature': 'hello'
        }
        # No AbortMessage
        raw_crash = {}

        predicate_result = rule.predicate(raw_crash, {}, processed_crash, {})
        assert predicate_result is False

    def test_predicate_empty_message(self):
        config = self.get_config()
        rule = AbortSignature(config)
        processed_crash = {
            'signature': 'hello'
        }
        raw_crash = {
            'AbortMessage': ''
        }
        predicate_result = rule.predicate(raw_crash, {}, processed_crash, {})
        assert predicate_result is False

    def test_action_success(self):
        config = self.get_config()
        rule = AbortSignature(config)
        processed_crash = {
            'signature': 'hello'
        }
        raw_crash = {
            'AbortMessage': 'unknown'
        }
        action_result = rule.action(raw_crash, {}, processed_crash, {})
        assert action_result is True
        assert processed_crash['original_signature'] == 'hello'
        assert processed_crash['signature'] == 'Abort | unknown | hello'

    def test_action_success_long_message(self):
        config = self.get_config()
        rule = AbortSignature(config)

        processed_crash = {
            'signature': 'hello'
        }
        raw_crash = {
            'AbortMessage': 'a' * 81
        }

        action_result = rule.action(raw_crash, {}, processed_crash, {})

        assert action_result is True
        assert processed_crash['original_signature'] == 'hello'
        expected_sig = 'Abort | {}... | hello'.format('a' * 77)
        assert processed_crash['signature'] == expected_sig

    def test_action_success_remove_unwanted_parts(self):
        config = self.get_config()
        rule = AbortSignature(config)

        processed_crash = {}
        raw_crash = {}

        # Test with just the "ABOR" thing at the start.
        processed_crash['signature'] = 'hello'
        raw_crash['AbortMessage'] = '[5392] ###!!! ABORT: foo bar line 42'

        action_result = rule.action(raw_crash, {}, processed_crash, {})

        assert action_result is True
        assert processed_crash['original_signature'] == 'hello'
        assert processed_crash['signature'] == 'Abort | foo bar line 42 | hello'

        # Test with a file name and line number.
        processed_crash['signature'] = 'hello'
        raw_crash['AbortMessage'] = (
            '[7616] ###!!! ABORT: unsafe destruction: file '
            'c:/builds/moz2_slave/m-rel-w32-00000000000000000000/build/src/'
            'dom/plugins/ipc/PluginModuleParent.cpp, line 777'
        )

        action_result = rule.action(raw_crash, {}, processed_crash, {})

        assert action_result is True
        assert processed_crash['original_signature'] == 'hello'
        assert processed_crash['signature'] == 'Abort | unsafe destruction | hello'

        # Test with a message that lacks interesting content.
        processed_crash['signature'] = 'hello'
        raw_crash['AbortMessage'] = '[204] ###!!! ABORT: file ?, '

        action_result = rule.action(raw_crash, {}, processed_crash, {})

        assert action_result is True
        assert processed_crash['original_signature'] == 'hello'
        assert processed_crash['signature'] == 'Abort | hello'

        # Test with another message that lacks interesting content.
        processed_crash['signature'] = 'hello'
        raw_crash['AbortMessage'] = (
            '[4648] ###!!! ABORT: file resource:///modules/sessionstore/'
            'SessionStore.jsm, line 1459'
        )

        action_result = rule.action(raw_crash, {}, processed_crash, {})

        assert action_result is True
        assert processed_crash['original_signature'] == 'hello'
        assert processed_crash['signature'] == 'Abort | hello'


class TestSigTrim(TestCase):

    def get_config(self):
        fake_processor = create_basic_fake_processor()
        return fake_processor.config

    def test_predicate_no_match(self):
        config = self.get_config()
        rule = SigTrim(config)

        processed_crash = {}
        predicate_result = rule.predicate({}, {}, processed_crash, {})
        assert predicate_result is False

        processed_crash['signature'] = 42
        predicate_result = rule.predicate({}, {}, processed_crash, {})
        assert predicate_result is False

    def test_predicate(self):
        config = self.get_config()
        rule = SigTrim(config)

        processed_crash = {
            'signature': 'fooo::baar'
        }

        predicate_result = rule.predicate({}, {}, processed_crash, {})
        assert predicate_result is True

    def test_action_success(self):
        config = self.get_config()
        rule = SigTrim(config)
        processed_crash = {
            'signature': 'all   good'
        }
        action_result = rule.action({}, {}, processed_crash, {})
        assert action_result is True
        assert processed_crash['signature'] == 'all   good'

        processed_crash['signature'] = 'all   good     '
        action_result = rule.action({}, {}, processed_crash, {})
        assert action_result is True
        assert processed_crash['signature'] == 'all   good'

        processed_crash['signature'] = '    all   good  '
        action_result = rule.action({}, {}, processed_crash, {})
        assert action_result is True
        assert processed_crash['signature'] == 'all   good'


class TestSigTrunc(TestCase):

    def test_predicate_no_match(self):
        processed_crash = {
            'signature': '0' * 100
        }
        fake_processor = create_basic_fake_processor()
        rule = SigTrunc(fake_processor.config)
        predicate_result = rule.predicate({}, {}, processed_crash, fake_processor)
        assert predicate_result is False

    def test_predicate(self):
        processed_crash = {
            'signature': '9' * 256
        }
        fake_processor = create_basic_fake_processor()
        rule = SigTrunc(fake_processor.config)
        predicate_result = rule.predicate({}, {}, processed_crash, fake_processor)
        assert predicate_result is True

    def test_action_success(self):
        processed_crash = {
            'signature': '9' * 256
        }
        fake_processor = create_basic_fake_processor()
        rule = SigTrunc(fake_processor.config)
        action_result = rule.action({}, {}, processed_crash, fake_processor)
        assert action_result is True
        assert len(processed_crash['signature']) == 255
        assert processed_crash['signature'].endswith('9...')


class TestStackwalkerErrorSignatureRule(TestCase):

    def test_predicate_no_match_signature(self):
        processed_crash = {
            'signature': '0' * 100
        }
        fake_processor = create_basic_fake_processor()
        rule = StackwalkerErrorSignatureRule(fake_processor.config)
        predicate_result = rule.predicate({}, {}, processed_crash, fake_processor)
        assert predicate_result is False

    def test_predicate_no_match_missing_mdsw_status_string(self):
        processed_crash = {
            'signature': 'EMPTY: like my soul'
        }
        fake_processor = create_basic_fake_processor()
        rule = StackwalkerErrorSignatureRule(fake_processor.config)
        predicate_result = rule.predicate({}, {}, processed_crash, fake_processor)
        assert predicate_result is False

    def test_predicate(self):
        processed_crash = {
            'signature': 'EMPTY: like my soul',
            'mdsw_status_string': 'catastrophic stackwalker failure'
        }
        fake_processor = create_basic_fake_processor()
        rule = StackwalkerErrorSignatureRule(fake_processor.config)
        predicate_result = rule.predicate({}, {}, processed_crash, fake_processor)
        assert predicate_result is True

    def test_action_success(self):
        processed_crash = {
            'signature': 'EMPTY: like my soul',
            'mdsw_status_string': 'catastrophic stackwalker failure'
        }
        fake_processor = create_basic_fake_processor()
        rule = StackwalkerErrorSignatureRule(fake_processor.config)
        action_result = rule.action({}, {}, processed_crash, fake_processor)
        assert action_result is True
        assert processed_crash['signature'] == 'EMPTY: like my soul; catastrophic stackwalker failure'


class TestSignatureWatchDogRule(TestCase):

    def get_config(self):
        config = DotDict({
            'c_signature': {
                'c_signature_tool_class': CSignatureTool,
                'maximum_frames_to_consider': 40,
                'collapse_arguments': True,
            },
            'java_signature': {
                'java_signature_tool_class': JavaSignatureTool,
            }
        })
        config.logger = sutil.FakeLogger()

        return CDotDict(config)

    def test_instantiation(self):
        config = self.get_config()
        srwd = SignatureRunWatchDog(config)

        assert isinstance(srwd.c_signature_tool, CSignatureTool)
        assert isinstance(srwd.java_signature_tool, JavaSignatureTool)

        assert srwd._get_crashing_thread({}) == 0

    def test_predicate(self):
        config = self.get_config()
        srwd = SignatureRunWatchDog(config)

        fake_processed_crash = {
            'signature': "I'm not real",
        }
        assert srwd.predicate({}, {}, fake_processed_crash, {}) is False

        fake_processed_crash = {
            'signature': "mozilla::`anonymous namespace''::RunWatchdog(void*)",
        }
        assert srwd.predicate({}, {}, fake_processed_crash, {}) is True

        fake_processed_crash = {
            'signature': "mozilla::(anonymous namespace)::RunWatchdog",
        }
        assert srwd.predicate({}, {}, fake_processed_crash, {}) is True

    def test_action(self):
        config = self.get_config()
        sgr = SignatureRunWatchDog(config)

        processed_crash = copy.deepcopy(sample_json_dump)
        # Set a fake signature
        processed_crash['signature'] = 'foo::bar'
        processor_meta = {
            'processor_notes': []
        }

        # the call to be tested
        assert sgr._action({}, {}, processed_crash, processor_meta) is True

        # Verify the signature has been re-generated based on thread 0.
        expected = (
            'shutdownhang | MsgWaitForMultipleObjects | '
            'F_1152915508__________________________________'
        )
        assert processed_crash['signature'] == expected
        assert processor_meta['processor_notes'] == []


class TestSignatureJitCategory(TestCase):

    def get_config(self):
        fake_processor = create_basic_fake_processor()
        return fake_processor.config

    def test_predicate_no_match(self):
        config = self.get_config()
        rule = SignatureJitCategory(config)

        processed_crash = {
            'classifications': {}
        }

        predicate_result = rule.predicate({}, {}, processed_crash, {})
        assert predicate_result is False

        processed_crash['classifications']['jit'] = {}
        predicate_result = rule.predicate({}, {}, processed_crash, {})
        assert predicate_result is False

        processed_crash['classifications']['jit']['category'] = ''
        predicate_result = rule.predicate({}, {}, processed_crash, {})
        assert predicate_result is False

    def test_predicate(self):
        config = self.get_config()
        rule = SignatureJitCategory(config)

        processed_crash = {
            'classifications': {
                'jit': {
                    'category': 'JIT Crash'
                }
            }
        }

        predicate_result = rule.predicate({}, {}, processed_crash, {})
        assert predicate_result is True

    def test_action_success(self):
        config = self.get_config()
        rule = SignatureJitCategory(config)

        processed_crash = {
            'signature': 'foo::bar',
            'classifications': {
                'jit': {
                    'category': 'JIT Crash'
                }
            }
        }
        processor_meta = {
            'processor_notes': []
        }

        action_result = rule.action({}, {}, processed_crash, processor_meta)
        assert action_result is True
        assert processed_crash['signature'] == 'jit | JIT Crash'
        expected = ['Signature replaced with a JIT Crash Category, was: "foo::bar"']
        assert processor_meta['processor_notes'] == expected


class TestSignatureIPCChannelError(TestCase):

    def get_config(self):
        fake_processor = create_basic_fake_processor()
        return fake_processor.config

    def test_predicate_no_match(self):
        config = self.get_config()
        rule = SignatureIPCChannelError(config)

        raw_crash = {}
        predicate_result = rule.predicate(raw_crash, {}, {}, {})
        assert predicate_result is False

        raw_crash['ipc_channel_error'] = ''
        predicate_result = rule.predicate(raw_crash, {}, {}, {})
        assert predicate_result is False

    def test_predicate(self):
        config = self.get_config()
        rule = SignatureIPCChannelError(config)

        raw_crash = {
            'ipc_channel_error': 'foo, bar'
        }

        predicate_result = rule.predicate(raw_crash, {}, {}, {})
        assert predicate_result is True

    def test_action_success(self):
        config = self.get_config()
        rule = SignatureIPCChannelError(config)

        processed_crash = {
            'signature': 'foo::bar'
        }
        raw_crash = {
            'ipc_channel_error': 'ipc' * 50
        }
        processor_meta = {
            'processor_notes': []
        }

        action_result = rule.action(raw_crash, {}, processed_crash, processor_meta)
        assert action_result is True
        expected = 'IPCError-content | {}'.format(('ipc' * 50)[:100])
        assert processed_crash['signature'] == expected
        expected = ['Signature replaced with an IPC Channel Error, was: "foo::bar"']
        assert processor_meta['processor_notes'] == expected

        # Now test with a browser crash.
        processed_crash['signature'] = 'foo::bar'
        raw_crash['additional_minidumps'] = 'browser'
        processor_meta = {
            'processor_notes': []
        }

        action_result = rule.action(raw_crash, {}, processed_crash, processor_meta)
        assert action_result is True

        expected = 'IPCError-browser | {}'.format(('ipc' * 50)[:100])
        assert processed_crash['signature'] == expected
        expected = ['Signature replaced with an IPC Channel Error, was: "foo::bar"']
        assert processor_meta['processor_notes'] == expected


class TestSignatureShutdownTimeout(TestCase):

    def get_config(self):
        fake_processor = create_basic_fake_processor()
        return fake_processor.config

    def test_predicate_no_match(self):
        config = self.get_config()
        rule = SignatureShutdownTimeout(config)

        raw_crash = DotDict()
        predicate_result = rule.predicate(raw_crash, {}, {}, {})
        assert predicate_result is False

    def test_predicate(self):
        config = self.get_config()
        rule = SignatureShutdownTimeout(config)

        raw_crash = {
            'AsyncShutdownTimeout': '{"foo": "bar"}'
        }

        predicate_result = rule.predicate(raw_crash, {}, {}, {})
        assert predicate_result is True

    def test_action_missing_valueerror(self):
        config = self.get_config()
        rule = SignatureShutdownTimeout(config)

        processed_crash = {
            'signature': 'foo'
        }
        raw_crash = {
            'AsyncShutdownTimeout': '{{{{'
        }
        processor_meta = {
            'processor_notes': []
        }
        action_result = rule.action(raw_crash, {}, processed_crash, processor_meta)
        assert action_result is True
        assert processed_crash['signature'] == 'AsyncShutdownTimeout | UNKNOWN'

        assert 'Error parsing AsyncShutdownTimeout:' in processor_meta['processor_notes'][0]
        assert 'Expected object or value' in processor_meta['processor_notes'][0]
        expected = 'Signature replaced with a Shutdown Timeout signature, was: "foo"'
        assert processor_meta['processor_notes'][1] == expected

    def test_action_missing_keyerror(self):
        config = self.get_config()
        rule = SignatureShutdownTimeout(config)

        processed_crash = {
            'signature': 'foo'
        }
        raw_crash = {
            'AsyncShutdownTimeout': json.dumps({
                'no': 'phase or condition'
            })
        }
        processor_meta = {
            'processor_notes': []
        }
        action_result = rule.action(raw_crash, {}, processed_crash, processor_meta)
        assert action_result is True
        assert processed_crash['signature'] == 'AsyncShutdownTimeout | UNKNOWN'

        expected = "Error parsing AsyncShutdownTimeout: 'phase'"
        assert processor_meta['processor_notes'][0] == expected
        expected = 'Signature replaced with a Shutdown Timeout signature, was: "foo"'
        assert processor_meta['processor_notes'][1] == expected

    def test_action_success(self):
        config = self.get_config()
        rule = SignatureShutdownTimeout(config)

        processed_crash = {
            'signature': 'foo'
        }
        processor_meta = {
            'processor_notes': []
        }
        raw_crash = {
            'AsyncShutdownTimeout': json.dumps({
                'phase': 'beginning',
                'conditions': [
                    {'name': 'A'},
                    {'name': 'B'},
                ]
            })
        }

        action_result = rule.action(raw_crash, {}, processed_crash, processor_meta)
        assert action_result is True

        assert processed_crash['signature'] == 'AsyncShutdownTimeout | beginning | A,B'
        expected = 'Signature replaced with a Shutdown Timeout signature, was: "foo"'
        assert processor_meta['processor_notes'][0] == expected

    def test_action_success_string_conditions(self):
        config = self.get_config()
        rule = SignatureShutdownTimeout(config)

        processed_crash = {
            'signature': 'foo'
        }
        processor_meta = {
            'processor_notes': []
        }
        raw_crash = {
            'AsyncShutdownTimeout': json.dumps({
                'phase': 'beginning',
                'conditions': ['A', 'B', 'C']
            })
        }

        action_result = rule.action(raw_crash, {}, processed_crash, processor_meta)
        assert action_result is True

        assert processed_crash['signature'] == 'AsyncShutdownTimeout | beginning | A,B,C'
        expected = 'Signature replaced with a Shutdown Timeout signature, was: "foo"'
        assert processor_meta['processor_notes'][0] == expected

    def test_action_success_empty_conditions_key(self):
        config = self.get_config()
        rule = SignatureShutdownTimeout(config)

        processed_crash = {
            'signature': 'foo'
        }
        processor_meta = {
            'processor_notes': []
        }
        raw_crash = {
            'AsyncShutdownTimeout': json.dumps({
                'phase': 'beginning',
                'conditions': []
            })
        }

        action_result = rule.action(raw_crash, {}, processed_crash, processor_meta)
        assert action_result is True

        assert processed_crash['signature'] == 'AsyncShutdownTimeout | beginning | (none)'
        expected = 'Signature replaced with a Shutdown Timeout signature, was: "foo"'
        assert processor_meta['processor_notes'][0] == expected


class TestSignatureIPCMessageName(TestCase):

    def get_config(self):
        fake_processor = create_basic_fake_processor()
        return fake_processor.config

    def test_predicate_no_match(self):
        config = self.get_config()
        rule = SignatureIPCMessageName(config)

        raw_crash = {}
        predicate_result = rule.predicate(raw_crash, {}, {}, {})
        assert predicate_result is False

        raw_crash['IPCMessageName'] = ''
        predicate_result = rule.predicate(raw_crash, {}, {}, {})
        assert predicate_result is False

    def test_predicate(self):
        config = self.get_config()
        rule = SignatureIPCMessageName(config)

        raw_crash = {
            'IPCMessageName': 'foo, bar'
        }
        processed_crash = {
            'signature': 'fooo::baar'
        }

        predicate_result = rule.predicate(raw_crash, {}, processed_crash, {})
        assert predicate_result is True

    def test_action_success(self):
        config = self.get_config()
        rule = SignatureIPCMessageName(config)
        processed_crash = {
            'signature': 'fooo::baar'
        }
        raw_crash = {
            'IPCMessageName': 'foo, bar'
        }
        action_result = rule.action(raw_crash, {}, processed_crash, {})
        assert action_result is True

        assert processed_crash['signature'] == 'fooo::baar | IPC_Message_Name=foo, bar'
