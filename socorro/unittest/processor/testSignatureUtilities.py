# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

import socorro.processor.signatureUtilities as sig
import socorro.lib.util as sutil

from socorro.lib.util import DotDict
from socorro.processor.signatureUtilities import JavaSignatureTool

import re

def assert_expected (expected, received):
    assert expected == received, 'expected:\n%s\nbut got:\n%s' % (expected,
                                                                  received)

def setupSigUtil(ig='ignored1', pr='pre1|pre2', si='fnNeedNumber'):
    config = sutil.DotDict()
    config.logger = sutil.FakeLogger()
    config.irrelevantSignatureRegEx = ig
    config.prefixSignatureRegEx = pr
    config.signaturesWithLineNumbersRegEx = si
    config.signatureSentinels = ('sentinel',
                                 ('sentinel2', lambda x: 'ff' in x),
                                )
    s = sig.CSignatureTool(config)
    return s, config

def testInit():
    """testInit: constructor test"""
    expectedRegEx = sutil.DotDict()
    expectedRegEx.irrelevantSignatureRegEx = re.compile('ignored1')
    expectedRegEx.prefixSignatureRegEx = re.compile('pre1|pre2')
    expectedRegEx.signaturesWithLineNumbersRegEx = re.compile('fnNeedNumber')
    fixupSpace = re.compile(r' (?=[\*&,])')
    fixupComma = re.compile(r',(?! )')
    fixupInteger = re.compile(r'(<|, )(\d+)([uUlL]?)([^\w])')

    s, c = setupSigUtil(expectedRegEx.irrelevantSignatureRegEx,
                        expectedRegEx.prefixSignatureRegEx,
                        expectedRegEx.signaturesWithLineNumbersRegEx)

    assert_expected(c, s.config)
    assert_expected(expectedRegEx.irrelevantSignatureRegEx,
                    s.irrelevantSignatureRegEx)
    assert_expected(expectedRegEx.prefixSignatureRegEx,
                    s.prefixSignatureRegEx)
    assert_expected(expectedRegEx.signaturesWithLineNumbersRegEx,
                    s.signaturesWithLineNumbersRegEx)
    assert_expected(fixupSpace,
                    s.fixupSpace)
    assert_expected(fixupComma,
                    s.fixupComma)
    assert_expected(fixupInteger,
                    s.fixupInteger)

def testNormalize():
    """testNormalize: bunch of variations"""
    s, c = setupSigUtil()
    a = [ (('module', 'fn', 'source', '23', '0xFFF'), 'fn'),
          (('module', 'fnNeedNumber', 's', '23', '0xFFF'), 'fnNeedNumber:23'),
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
        assert_expected(e,r)

def testGenerate1():
    """testGenerate1: simple"""
    s, c = setupSigUtil('a|b|c', 'd|e|f')
    a = [x for x in 'abcdefghijklmnopqrstuvwxyz']
    e = 'd | e | f | g'
    sig, notes = s.generate(a)
    assert_expected(e,sig)

    a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
    e = 'd | e | f | g'
    sig, notes = s.generate(a)
    assert_expected(e,sig)

def testGenerate2():
    """testGenerate2: hang"""
    s, c = setupSigUtil('a|b|c', 'd|e|f')
    a = [x for x in 'abcdefghijklmnopqrstuvwxyz']
    e = 'hang | d | e | f | g'
    sig, notes = s.generate(a, hang_type=-1)
    assert_expected(e,sig)

    a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
    e = 'hang | d | e | f | g'
    sig, notes = s.generate(a, hang_type=-1)
    assert_expected(e,sig)

    a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
    e = 'd | e | f | g'
    sig, notes = s.generate(a, hang_type=0)
    assert_expected(e,sig)

    a = [x for x in 'abcdaeafagahijklmnopqrstuvwxyz']
    e = 'chromehang | d | e | f | g'
    sig, notes = s.generate(a, hang_type=1)
    assert_expected(e,sig)


def testGenerate2a():
    """testGenerate2a: way too long"""
    s, c = setupSigUtil('a|b|c', 'd|e|f')
    a = [x for x in 'abcdefghijklmnopqrstuvwxyz']
    a[3] = a[3] * 70
    a[4] = a[4] * 70
    a[5] = a[5] * 70
    a[6] = a[6] * 70
    a[7] = a[7] * 70
    e = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd" \
        "dd | eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee" \
        "eeeeeee | ffffffffffffffffffffffffffffffffffffffffffffffffffffffffff" \
        "ffffffffffff | ggggggggggggggggggggggggggggggggg..."
    sig, notes = s.generate(a)
    assert_expected(e,sig)
    e = "hang | ddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd" \
        "ddddddddd | eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee" \
        "eeeeeeeeeeeeee | fffffffffffffffffffffffffffffffffffffffffffffffffff" \
        "fffffffffffffffffff | gggggggggggggggggggggggggg..."
    sig, notes = s.generate(a, hang_type=-1)
    assert_expected(e,sig)

def testGenerate3():
    """testGenerate3: simple sentinel"""
    s, c = setupSigUtil('a|b|c', 'd|e|f')
    a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
    a[7] = 'sentinel'
    e = 'sentinel'
    sig, notes = s.generate(a)
    assert_expected(e,sig)

    s, c  = setupSigUtil('a|b|c|sentinel', 'd|e|f')
    e = 'f | e | d | i'
    sig, notes = s.generate(a)
    assert_expected(e,sig)

def testGenerate4():
    """testGenerate4: tuple sentinel"""
    s, c = setupSigUtil('a|b|c', 'd|e|f')
    a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
    a[7] = 'sentinel2'
    e = 'd | e | f | g'
    sig, notes = s.generate(a)
    assert_expected(e,sig)

    s, c = setupSigUtil('a|b|c', 'd|e|f')
    a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
    a[7] = 'sentinel2'
    a[22] = 'ff'
    e = 'sentinel2'
    sig, notes = s.generate(a)
    assert_expected(e,sig)

    s, c = setupSigUtil('a|b|c|sentinel2', 'd|e|f')
    a = [x for x in 'abcdefghabcfaeabdijklmnopqrstuvwxyz']
    a[7] = 'sentinel2'
    a[22] = 'ff'
    e = 'f | e | d | i'
    sig, notes = s.generate(a)
    assert_expected(e,sig)


class TestCase(unittest.TestCase):
    def test_generate_signature_1(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 17
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = "EMPTY: Java stack trace not in expected format"
        assert_expected(e, sig)
        e = ['JavaSignatureTool: stack trace not '
             'in expected format']
        assert_expected(e, notes)

    def test_generate_signature_2(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('SomeJavaException: totally made up  \n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java:666)')
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = ('SomeJavaException: totally made up '
             'at org.mozilla.lars.myInvention('
             'larsFile.java)')
        assert_expected(e, sig)
        e = []
        assert_expected(e, notes)

    def test_generate_signature_3(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('SomeJavaException: totally made up  \n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java)')
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = ('SomeJavaException: totally made up '
             'at org.mozilla.lars.myInvention('
             'larsFile.java)')
        assert_expected(e, sig)
        e = []
        assert_expected(e, notes)

    def test_generate_signature_4(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('   SomeJavaException: %s  \n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java)' % ('t'*1000))
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = ('SomeJavaException: '
             'at org.mozilla.lars.myInvention('
             'larsFile.java)')
        assert_expected(e, sig)
        e = ['JavaSignatureTool: dropped Java exception description due to '
             'length']
        assert_expected(e, notes)

    def test_generate_signature_4(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('   SomeJavaException: %s  \n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java:1234)' % ('t'*1000))
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = ('SomeJavaException: '
             'at org.mozilla.lars.myInvention('
             'larsFile.java)')
        assert_expected(e, sig)
        e = ['JavaSignatureTool: dropped Java exception description due to '
             'length']
        assert_expected(e, notes)

    def test_generate_signature_5(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('   SomeJavaException\n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java:1234)')
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = ('SomeJavaException: '
             'at org.mozilla.lars.myInvention('
             'larsFile.java)')
        assert_expected(e, sig)
        e = ['JavaSignatureTool: stack trace line 1 is '
             'not in the expected format']
        assert_expected(e, notes)

    def test_generate_signature_6(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 'SomeJavaException: totally made up  \n'
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = 'SomeJavaException: totally made up'
        assert_expected(e, sig)
        e = ['JavaSignatureTool: stack trace line 2 is empty']
        assert_expected(e, notes)

    def test_generate_signature_7(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 'SomeJavaException: totally made up  '
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = 'SomeJavaException: totally made up'
        assert_expected(e, sig)
        e = ['JavaSignatureTool: stack trace line 2 is missing']
        assert_expected(e, notes)

    def test_generate_signature_8(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = 'SomeJavaException: totally made up  '
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = 'SomeJavaException: totally made up'
        assert_expected(e, sig)
        e = ['JavaSignatureTool: stack trace line 2 is missing']
        assert_expected(e, notes)

    def test_generate_signature_9(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('   SomeJavaException: totally made up  \n'
                            'at org.mozilla.lars.myInvention('
                            '%slarsFile.java:1234)' % ('t'*1000))
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = ('SomeJavaException: '
             'at org.mozilla.lars.myInvention('
             '%s...' % ('t' * 201))
        assert_expected(e, sig)
        e = ['JavaSignatureTool: dropped Java exception description due to '
             'length',
             'SignatureTool: signature truncated due to length']
        assert_expected(e, notes)

    def test_generate_signature_10_no_interference(self):
        config = DotDict()
        j = JavaSignatureTool(config)
        java_stack_trace = ('SomeJavaException: totally made up  \n'
                            'at org.mozilla.lars.myInvention('
                            'larsFile.java:@abef1234)')
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = ('SomeJavaException: totally made up '
             'at org.mozilla.lars.myInvention('
             'larsFile.java:@abef1234)')
        assert_expected(e, sig)
        e = []
        assert_expected(e, notes)


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
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = ('java.lang.IllegalArgumentException: '
             'Given view not a child of android.widget.AbsoluteLayout@<addr>: '
             'at android.view.ViewGroup.updateViewLayout(ViewGroup.java)')
        assert_expected(e, sig)
        e = []
        assert_expected(e, notes)


    def test_generate_signature_12_replace_address_and_colon(self):
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
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = ('java.lang.IllegalArgumentException: '
             'Given view not a child of android.widget.AbsoluteLayout@<addr>: '
             'at android.view.ViewGroup.updateViewLayout(ViewGroup.java)')
        assert_expected(e, sig)
        e = []
        assert_expected(e, notes)

    def test_generate_signature_13_replace_address_and_colon(self):
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
        sig, notes = j.generate(java_stack_trace, delimiter=' ')
        e = ('java.lang.IllegalArgumentException: '
             'Receiver not registered: '
             'org.mozilla.gecko.GeckoConnectivityReceiver@<addr>: '
             'at android.app.LoadedApk.forgetReceiverDispatcher'
             '(LoadedApk.java)')
        assert_expected(e, sig)
        e = []
        assert_expected(e, notes)


