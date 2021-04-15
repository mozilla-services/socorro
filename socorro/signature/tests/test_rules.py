# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
import importlib
import json
import re
from unittest import mock

import pytest

# NOTE(willkg): We do this so that we can extract signature generation into its
# own namespace as an external library. This allows the tests to run if it's in
# "siggen" or "socorro.signature".
BASE_MODULE = ".".join(__name__.split(".")[:-2])
rules = importlib.import_module(BASE_MODULE + ".rules")
generator = importlib.import_module(BASE_MODULE + ".generator")


@pytest.mark.parametrize(
    "frame, expected_function",
    [
        # Don't die on missing data
        ({}, None),
        # If file is missing, it should just return the same frame
        ({"function": "panic"}, "panic"),
        # Fix function if (file, function) are in lookup table
        (
            {
                "file": "git:github.com/rust-lang/rust:src/libstd/panicking.rs:91856ed52c58aa5ba66a015354d1cc69e9779bdf",  # noqa
                "function": "begin_panic_fmt",
            },
            "std::panicking::begin_panic_fmt",
        ),
    ],
)
def test_fix_missing_module(frame, expected_function):
    actual_function = rules.fix_missing_module(frame).get("function")
    assert actual_function == expected_function


class TestCSignatureTool:
    @staticmethod
    def setup_config_c_sig_tool(
        ig=["ignored1"],
        pr=["pre1", "pre2"],
        si=["fnNeedNumber"],
        td=[r"foo32\.dll.*"],
        ss=("sentinel", ("sentinel2", lambda x: "ff" in x)),
    ):
        with mock.patch(BASE_MODULE + ".rules.siglists_utils") as mocked_siglists:
            mocked_siglists.IRRELEVANT_SIGNATURE_RE = ig
            mocked_siglists.PREFIX_SIGNATURE_RE = pr
            mocked_siglists.SIGNATURES_WITH_LINE_NUMBERS_RE = si
            mocked_siglists.TRIM_DLL_SIGNATURE_RE = td
            mocked_siglists.SIGNATURE_SENTINELS = ss
            return rules.CSignatureTool()

    def test_c_config_tool_init(self):
        """test_C_config_tool_init: constructor test"""
        exp_irrelevant_signature_re = re.compile(r"ignored1")
        exp_prefix_signature_re = re.compile(r"pre1|pre2")
        exp_signatures_with_line_numbers_re = re.compile(r"fnNeedNumber")
        fixup_space = re.compile(r" (?=[\*&,])")
        fixup_comma = re.compile(r",(?! )")

        s = self.setup_config_c_sig_tool()

        assert exp_irrelevant_signature_re.pattern == s.irrelevant_signature_re.pattern
        assert exp_prefix_signature_re.pattern == s.prefix_signature_re.pattern
        assert (
            exp_signatures_with_line_numbers_re.pattern
            == s.signatures_with_line_numbers_re.pattern
        )

        assert fixup_space.pattern == s.fixup_space.pattern
        assert fixup_comma.pattern == s.fixup_comma.pattern

    def test_normalize_frame(self):
        """test_normalize: bunch of variations"""
        s = self.setup_config_c_sig_tool()
        a = [
            (("module", "", "source/", "23", "0xFFF"), "source#23"),
            (("module", "", "source\\", "23", "0xFFF"), "source#23"),
            (("module", "", "/a/b/c/source", "23", "0xFFF"), "source#23"),
            (("module", "", "\\a\\b\\c\\source", "23", "0xFFF"), "source#23"),
            (("module", "", "\\a\\b\\c\\source", "23", "0xFFF"), "source#23"),
            (("module", "", "\\a\\b\\c\\source", "", "0xFFF"), "module@0xFFF"),
            (("module", "", "", "23", "0xFFF"), "module@0xFFF"),
            (("module", "", "", "", "0xFFF"), "module@0xFFF"),
            ((None, "", "", "", "0xFFF"), "@0xFFF"),
            # Make sure frame normalization uses the right function: normalize
            # Rust frame (has a Rust fingerprint)
            (
                (
                    "module",
                    "expect_failed::h7f635057bfba806a",
                    "hg:hg.mozilla.org/a/b:servio/wrapper.rs:44444444444",
                    "23",
                    "0xFFF",
                ),
                "expect_failed",
            ),
        ]
        for args, e in a:
            r = s.normalize_frame(*args)
            assert e == r

    @pytest.mark.parametrize(
        "function, line, expected",
        [
            # Verify function and line number handling
            ("fn", "23", "fn"),
            ("fnNeedNumber", "23", "fnNeedNumber:23"),
            # Remove function arguments
            ("f( *s)", "23", "f"),
            ("f( &s)", "23", "f"),
            ("f( *s , &n)", "23", "f"),
            ("f3(s,t,u)", "23", "f3"),
            ("operator()(s,t,u)", "23", "operator()"),
            ("::(anonymous namespace)::f3(s,t,u)", "23", "::(anonymous namespace)::f3"),
            (
                "mozilla::layers::D3D11YCbCrImage::GetAsSourceSurface()",
                "23",
                "mozilla::layers::D3D11YCbCrImage::GetAsSourceSurface",
            ),
            (
                "mozilla::layers::BasicImageLayer::Paint(mozilla::gfx::DrawTarget*, mozilla::gfx::PointTyped<mozilla::gfx::UnknownUnits, float> const&, mozilla::layers::Layer*)",
                "23",  # noqa
                "mozilla::layers::BasicImageLayer::Paint",
            ),
            (
                "void nsDocumentViewer::DestroyPresShell()",
                "23",
                "nsDocumentViewer::DestroyPresShell",
            ),
            (
                "bool CCGraphBuilder::BuildGraph(class js::SliceBudget& const)",
                "23",
                "CCGraphBuilder::BuildGraph",
            ),
            # Handle converting types to generic
            ("f<3>(s,t,u)", "23", "f<T>"),
            ("Alpha<Bravo<Charlie>, Delta>::Echo<Foxtrot>", "23", "Alpha<T>::Echo<T>"),
            (
                "thread_start<unsigned int (__cdecl*)(void* __ptr64)>",
                "23",
                "thread_start<T>",
            ),
            # Handle prefixes and return types
            (
                "class JSObject* DoCallback<JSObject*>(class JS::CallbackTracer*, class JSObject**, const char*)",
                "23",  # noqa
                "DoCallback<T>",
            ),
            # But don't run drop_prefix_and_return_types for operator overloading
            # functions
            (
                "JS::Heap<JSObject*>::operator JSObject* const &()",
                "23",
                "JS::Heap<T>::operator JSObject* const&",
            ),
            # Drop cv/ref qualifiers at end
            (
                "JSObject::allocKindForTenure const",
                "23",
                "JSObject::allocKindForTenure",
            ),
            (
                "mozilla::jni::GlobalRef<mozilla::jni::Object>::operator=(mozilla::jni::Ref<mozilla::jni::Object, _jobject*> const&)&",
                "23",  # noqa
                "mozilla::jni::GlobalRef<T>::operator=",
            ),
            # Normalize anonymous namespace
            ("`anonymous namespace'::foo", "23", "(anonymous namespace)::foo"),
            ("(anonymous namespace)::foo", "23", "(anonymous namespace)::foo"),
            # Normalize lambda numbers
            (
                "ShutdownWorkThreads::$_52::__invoke",
                "23",
                "ShutdownWorkThreads::$::__invoke",
            ),
        ],
    )
    def test_normalize_cpp_function(self, function, line, expected):
        """Test normalization for cpp functions"""
        s = self.setup_config_c_sig_tool()
        assert s.normalize_cpp_function(function, line) == expected

    @pytest.mark.parametrize(
        "function, line, expected",
        [
            # Verify removal of fingerprints
            ("expect_failed::h7f635057bfba806a", "23", "expect_failed"),
            ("expect_failed::h7f6350::blah", "23", "expect_failed::h7f6350::blah"),
            # Handle prefixes, return types, types, and traits
            (
                "static void servo_arc::Arc<style::gecko_properties::ComputedValues>::drop_slow<style::gecko_properties::ComputedValues>()",
                "23",  # noqa
                "servo_arc::Arc<T>::drop_slow<T>",
            ),
            (
                "static void core::ptr::drop_in_place<style::stylist::CascadeData>(struct style::stylist::CascadeData*)",
                "23",  # noqa
                "core::ptr::drop_in_place<T>",
            ),
            # Handle trait methods by not collapsing them
            (
                "<rayon_core::job::HeapJob<BODY> as rayon_core::job::Job>::execute",
                "23",
                "<rayon_core::job::HeapJob<BODY> as rayon_core::job::Job>::execute",
            ),
        ],
    )
    def test_normalize_rust_function(self, function, line, expected):
        """Test normalization for Rust functions"""
        s = self.setup_config_c_sig_tool()
        assert s.normalize_rust_function(function, line) == expected

    def test_generate_1(self):
        """test_generate_1: simple"""
        s = self.setup_config_c_sig_tool(ig=["a", "b", "c"], pr=["d", "e", "f"])
        a = list("abcdefghijklmnopqrstuvwxyz")
        sig, notes, debug_notes = s.generate(a)
        assert sig == "d | e | f | g"

        a = list("abcdaeafagahijklmnopqrstuvwxyz")
        sig, notes, debug_notes = s.generate(a)
        assert sig == "d | e | f | g"

    def test_generate_2(self):
        """test_generate_2: hang"""
        s = self.setup_config_c_sig_tool(ig=["a", "b", "c"], pr=["d", "e", "f"])
        a = list("abcdefghijklmnopqrstuvwxyz")
        sig, notes, debug_notes = s.generate(a, hang_type=-1)
        assert sig == "hang | d | e | f | g"

        a = list("abcdaeafagahijklmnopqrstuvwxyz")
        sig, notes, debug_notes = s.generate(a, hang_type=-1)
        assert sig == "hang | d | e | f | g"

        a = list("abcdaeafagahijklmnopqrstuvwxyz")
        sig, notes, debug_notes = s.generate(a, hang_type=0)
        assert sig == "d | e | f | g"

        a = list("abcdaeafagahijklmnopqrstuvwxyz")
        sig, notes, debug_notes = s.generate(a, hang_type=1)
        assert sig == "chromehang | d | e | f | g"

    def test_generate_2a(self):
        """test_generate_2a: way too long"""
        s = self.setup_config_c_sig_tool(ig=["a", "b", "c"], pr=["d", "e", "f"])
        a = list("abcdefghijklmnopqrstuvwxyz")
        a[3] = a[3] * 70
        a[4] = a[4] * 70
        a[5] = a[5] * 70
        a[6] = a[6] * 70
        a[7] = a[7] * 70
        expected = (
            "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd | "
            "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee | "
            "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff | "
            "gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg"
        )
        sig, notes, debug_notes = s.generate(a)
        assert sig == expected
        expected = (
            "hang | "
            "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd | "
            "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee | "
            "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff | "
            "gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg"
        )
        sig, notes, debug_notes = s.generate(a, hang_type=-1)
        assert sig == expected

    def test_generate_3(self):
        """test_generate_3: simple sentinel"""
        s = self.setup_config_c_sig_tool(ig=["a", "b", "c"], pr=["d", "e", "f"])
        a = list("abcdefghabcfaeabdijklmnopqrstuvwxyz")
        a[7] = "sentinel"
        sig, notes, debug_notes = s.generate(a)
        assert sig == "sentinel"

        s = self.setup_config_c_sig_tool(
            ig=["a", "b", "c", "sentinel"], pr=["d", "e", "f"]
        )
        sig, notes, debug_notes = s.generate(a)
        assert sig == "f | e | d | i"

    def test_generate_4(self):
        """test_generate_4: tuple sentinel"""
        s = self.setup_config_c_sig_tool(ig=["a", "b", "c"], pr=["d", "e", "f"])
        a = list("abcdefghabcfaeabdijklmnopqrstuvwxyz")
        a[7] = "sentinel2"
        sig, notes, debug_notes = s.generate(a)
        assert sig == "d | e | f | g"

        s = self.setup_config_c_sig_tool(ig=["a", "b", "c"], pr=["d", "e", "f"])
        a = list("abcdefghabcfaeabdijklmnopqrstuvwxyz")
        a[7] = "sentinel2"
        a[22] = "ff"
        sig, notes, debug_notes = s.generate(a)
        assert sig == "sentinel2"

        s = self.setup_config_c_sig_tool(
            ig=["a", "b", "c", "sentinel2"], pr=["d", "e", "f"]
        )
        a = list("abcdefghabcfaeabdijklmnopqrstuvwxyz")
        a[7] = "sentinel2"
        a[22] = "ff"
        sig, notes, debug_notes = s.generate(a)
        assert sig == "f | e | d | i"

    def test_generate_with_merged_dll(self):
        sig_tool = self.setup_config_c_sig_tool(ig=["a", "b", "c"], pr=["d", "e", "f"])
        source_list = [
            "a",
            "d",
            "foo32.dll@0x231423",
            "foo32.dll",
            "foo32.dll@0x42",
            "g",
        ]
        sig, notes, debug_notes = sig_tool.generate(source_list)
        assert sig == "d | foo32.dll | g"

        source_list = ["foo32.dll", "foo32.dll@0x231423", "g"]
        sig, notes, debug_notes = sig_tool.generate(source_list)
        assert sig == "foo32.dll | g"


class TestJavaSignatureTool:
    def test_bad_stack(self):
        j = rules.JavaSignatureTool()
        java_stack_trace = 17
        sig, notes, debug_notes = j.generate(java_stack_trace, delimiter=": ")
        assert sig == "EMPTY: Java stack trace not in expected format"
        assert notes == ["JavaSignatureTool: stack trace not in expected format"]

    def test_basic_stack_frame_with_line_number(self):
        j = rules.JavaSignatureTool()
        java_stack_trace = (
            "SomeJavaException: totally made up  \n"
            "at org.mozilla.lars.myInvention(larsFile.java:666)"
        )
        sig, notes, debug_notes = j.generate(java_stack_trace, delimiter=": ")
        e = "SomeJavaException: totally made up at org.mozilla.lars.myInvention(larsFile.java)"
        assert sig == e
        assert notes == []

    def test_basic_stack_frame(self):
        j = rules.JavaSignatureTool()
        java_stack_trace = (
            "SomeJavaException: totally made up  \n"
            "at org.mozilla.lars.myInvention(larsFile.java)"
        )
        sig, notes, debug_notes = j.generate(java_stack_trace, delimiter=": ")
        e = "SomeJavaException: totally made up at org.mozilla.lars.myInvention(larsFile.java)"
        assert sig == e
        assert notes == []

    def test_long_exception_description(self):
        j = rules.JavaSignatureTool()
        java_stack_trace = (
            "   SomeJavaException: %s \nat org.mozilla.lars.myInvention(larsFile.java)"
            % ("t" * 1000)
        )
        sig, notes, debug_notes = j.generate(java_stack_trace, delimiter=": ")
        expected = "SomeJavaException: at org.mozilla.lars.myInvention(larsFile.java)"
        assert sig == expected
        expected = [
            "JavaSignatureTool: dropped Java exception description due to length"
        ]
        assert notes == expected

    def test_long_exception_description_with_line_number(self):
        j = rules.JavaSignatureTool()
        java_stack_trace = (
            "   SomeJavaException: %s  \nat org.mozilla.lars.myInvention(larsFile.java:1234)"
            % ("t" * 1000)
        )
        sig, notes, debug_notes = j.generate(java_stack_trace, delimiter=": ")
        expected = "SomeJavaException: at org.mozilla.lars.myInvention(larsFile.java)"
        assert sig == expected
        expected = [
            "JavaSignatureTool: dropped Java exception description due to length"
        ]
        assert notes == expected

    def test_no_description(self):
        j = rules.JavaSignatureTool()
        java_stack_trace = (
            "   SomeJavaException\n"
            "at org.mozilla.lars.myInvention(larsFile.java:1234)"
        )
        sig, notes, debug_notes = j.generate(java_stack_trace, delimiter=": ")
        e = "SomeJavaException: at org.mozilla.lars.myInvention(larsFile.java)"
        assert sig == e
        e = ["JavaSignatureTool: stack trace line 1 is not in the expected format"]
        assert notes == e

    def test_frame_with_line_ending_but_missing_second_line(self):
        j = rules.JavaSignatureTool()
        java_stack_trace = "SomeJavaException: totally made up  \n"
        sig, notes, debug_notes = j.generate(java_stack_trace, delimiter=": ")
        e = "SomeJavaException: totally made up"
        assert sig == e
        e = ["JavaSignatureTool: stack trace line 2 is missing"]
        assert notes == e

    def test_frame_missing_second_line(self):
        j = rules.JavaSignatureTool()
        java_stack_trace = "SomeJavaException: totally made up  "
        sig, notes, debug_notes = j.generate(java_stack_trace, delimiter=": ")
        e = "SomeJavaException: totally made up"
        assert sig == e
        e = ["JavaSignatureTool: stack trace line 2 is missing"]
        assert notes == e

    def test_frame_with_leading_whitespace(self):
        j = rules.JavaSignatureTool()
        java_stack_trace = (
            "   SomeJavaException: totally made up  \n"
            "at org.mozilla.lars.myInvention("
            "foolarsFile.java:1234)"
        )
        sig, notes, debug_notes = j.generate(java_stack_trace, delimiter=": ")
        expected = "SomeJavaException: totally made up at org.mozilla.lars.myInvention(foolarsFile.java)"
        assert sig == expected

    def test_no_interference(self):
        # In general addresses of the form ``@xxxxxxxx`` are to be replaced
        # with the literal ``<addr>``, however in this case, the hex address is
        # not in the expected location and should therefore be left alone
        j = rules.JavaSignatureTool()
        java_stack_trace = (
            "SomeJavaException: totally made up  \n"
            "at org.mozilla.lars.myInvention(larsFile.java:@abef1234)"
        )
        sig, notes, debug_notes = j.generate(java_stack_trace, delimiter=" ")
        e = (
            "SomeJavaException totally made up "
            "at org.mozilla.lars.myInvention("
            "larsFile.java:@abef1234)"
        )
        assert sig == e
        assert notes == []

    def test_replace_address(self):
        j = rules.JavaSignatureTool()
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
        sig, notes, debug_notes = j.generate(java_stack_trace, delimiter=": ")
        e = (
            "java.lang.IllegalArgumentException: "
            "Given view not a child of android.widget.AbsoluteLayout@<addr>: "
            "at android.view.ViewGroup.updateViewLayout(ViewGroup.java)"
        )
        assert sig == e
        assert notes == []

    def test_replace_address_with_trailing_text(self):
        j = rules.JavaSignatureTool()
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
        sig, notes, debug_notes = j.generate(java_stack_trace, delimiter=": ")
        e = (
            "android.view.WindowManager$BadTokenException: "
            "Unable to add window -- token android.os.BinderProxy@<addr> "
            "is not valid; is your activity running? "
            "at android.view.ViewRoot.setView(ViewRoot.java)"
        )
        assert sig == e
        assert notes == []

    def test_replace_address_trailing_whitespace(self):
        j = rules.JavaSignatureTool()
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
        sig, notes, debug_notes = j.generate(java_stack_trace, delimiter=": ")
        e = (
            "java.lang.IllegalArgumentException: "
            "Receiver not registered: "
            "org.mozilla.gecko.GeckoNetworkManager@<addr>: "
            "at android.app.LoadedApk.forgetReceiverDispatcher(LoadedApk.java)"
        )
        assert sig == e
        assert notes == []


#  rules testing section

FRAMES_FROM_JSON_DUMP = {
    "frames": [
        {
            "frame": 0,
            "function": "NtWaitForMultipleObjects",
            "function_offset": "0x15",
            "module": "ntdll.dll",
            "module_offset": "0x2015d",
            "offset": "0x77ad015d",
            "registers": {
                "eax": "0x00000040",
                "ebp": "0x0025e968",
                "ebx": "0x0025e91c",
                "ecx": "0x00000000",
                "edi": "0x00000000",
                "edx": "0x00000000",
                "efl": "0x00200246",
                "eip": "0x77ad015d",
                "esi": "0x00000004",
                "esp": "0x0025e8cc",
            },
            "trust": "context",
        },
        {
            "frame": 1,
            "function": "WaitForMultipleObjectsEx",
            "function_offset": "0xff",
            "module": "KERNELBASE.dll",
            "module_offset": "0x115f6",
            "offset": "0x775e15f6",
            "trust": "cfi",
        },
        {
            "frame": 2,
            "function": "WaitForMultipleObjectsExImplementation",
            "function_offset": "0x8d",
            "module": "kernel32.dll",
            "module_offset": "0x119f7",
            "offset": "0x766119f7",
            "trust": "cfi",
        },
        {
            "frame": 3,
            "function": "RealMsgWaitForMultipleObjectsEx",
            "function_offset": "0xe1",
            "module": "user32.dll",
            "module_offset": "0x20869",
            "offset": "0x77370869",
            "trust": "cfi",
        },
        {
            "frame": 4,
            "function": "MsgWaitForMultipleObjects",
            "function_offset": "0x1e",
            "module": "user32.dll",
            "module_offset": "0x20b68",
            "offset": "0x77370b68",
            "trust": "cfi",
        },
        {
            "file": "F117835525________________________________________",
            "frame": 5,
            "function": "F_1152915508__________________________________",
            "function_offset": "0xbb",
            "line": 118,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x36a13b",
            "offset": "0x5e3aa13b",
            "trust": "cfi",
        },
        {
            "file": "F_851861807_______________________________________",
            "frame": 6,
            "function": "F2166389______________________________________",
            "function_offset": "0xe5",
            "line": 552,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x35faf5",
            "offset": "0x5e39faf5",
            "trust": "cfi",
        },
        {
            "file": "F_851861807_______________________________________",
            "frame": 7,
            "function": "F_917831355___________________________________",
            "function_offset": "0x29b",
            "line": 488,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x360a7b",
            "offset": "0x5e3a0a7b",
            "trust": "cfi",
        },
        {
            "file": "F_851861807_______________________________________",
            "frame": 8,
            "function": "F1315696776________________________________",
            "function_offset": "0xd",
            "line": 439,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x35e2fd",
            "offset": "0x5e39e2fd",
            "trust": "cfi",
        },
        {
            "file": "F_766591945_______________________________________",
            "frame": 9,
            "function": "F_1428703866________________________________",
            "function_offset": "0xc1",
            "line": 203,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x35bf21",
            "offset": "0x5e39bf21",
            "trust": "cfi",
        },
    ],
    "threads_index": 0,
    "frame_count": 32,
}

FRAMES_FROM_JSON_DUMP_WITH_TEMPLATES = {
    "frames": [
        {
            "frame": 0,
            "function": "NtWaitForMultipleObjects",
            "function_offset": "0x15",
            "module": "ntdll.dll",
            "module_offset": "0x2015d",
            "offset": "0x77ad015d",
            "registers": {
                "eax": "0x00000040",
                "ebp": "0x0025e968",
                "ebx": "0x0025e91c",
                "ecx": "0x00000000",
                "edi": "0x00000000",
                "edx": "0x00000000",
                "efl": "0x00200246",
                "eip": "0x77ad015d",
                "esi": "0x00000004",
                "esp": "0x0025e8cc",
            },
            "trust": "context",
        },
        {
            "frame": 1,
            "function": "Alpha<Bravo<Charlie>, Delta>::Echo<Foxtrot>",
            "function_offset": "0xff",
            "module": "KERNELBASE.dll",
            "module_offset": "0x115f6",
            "offset": "0x775e15f6",
            "trust": "cfi",
        },
        {
            "frame": 2,
            "function": "WaitForMultipleObjectsExImplementation",
            "function_offset": "0x8d",
            "module": "kernel32.dll",
            "module_offset": "0x119f7",
            "offset": "0x766119f7",
            "trust": "cfi",
        },
        {
            "frame": 3,
            "function": "RealMsgWaitForMultipleObjectsEx(void **fakeargs)",
            "function_offset": "0xe1",
            "module": "user32.dll",
            "module_offset": "0x20869",
            "offset": "0x77370869",
            "trust": "cfi",
        },
        {
            "frame": 4,
            "function": "MsgWaitForMultipleObjects",
            "function_offset": "0x1e",
            "module": "user32.dll",
            "module_offset": "0x20b68",
            "offset": "0x77370b68",
            "trust": "cfi",
        },
        {
            "file": "F117835525________________________________________",
            "frame": 5,
            "function": "F_1152915508__________________________________",
            "function_offset": "0xbb",
            "line": 118,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x36a13b",
            "offset": "0x5e3aa13b",
            "trust": "cfi",
        },
        {
            "file": "F_851861807_______________________________________",
            "frame": 6,
            "function": "F2166389______________________________________",
            "function_offset": "0xe5",
            "line": 552,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x35faf5",
            "offset": "0x5e39faf5",
            "trust": "cfi",
        },
        {
            "file": "F_851861807_______________________________________",
            "frame": 7,
            "function": "F_917831355___________________________________",
            "function_offset": "0x29b",
            "line": 488,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x360a7b",
            "offset": "0x5e3a0a7b",
            "trust": "cfi",
        },
        {
            "file": "F_851861807_______________________________________",
            "frame": 8,
            "function": "F1315696776________________________________",
            "function_offset": "0xd",
            "line": 439,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x35e2fd",
            "offset": "0x5e39e2fd",
            "trust": "cfi",
        },
        {
            "file": "F_766591945_______________________________________",
            "frame": 9,
            "function": "F_1428703866________________________________",
            "function_offset": "0xc1",
            "line": 203,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x35bf21",
            "offset": "0x5e39bf21",
            "trust": "cfi",
        },
    ],
    "threads_index": 0,
    "total_frames": 32,
}

FRAMES_FROM_JSON_DUMP_WITH_TEMPLATES_AND_SPECIAL_CASE = {
    "frames": [
        {
            "frame": 0,
            "function": "NtWaitForMultipleObjects",
            "function_offset": "0x15",
            "module": "ntdll.dll",
            "module_offset": "0x2015d",
            "offset": "0x77ad015d",
            "registers": {
                "eax": "0x00000040",
                "ebp": "0x0025e968",
                "ebx": "0x0025e91c",
                "ecx": "0x00000000",
                "edi": "0x00000000",
                "edx": "0x00000000",
                "efl": "0x00200246",
                "eip": "0x77ad015d",
                "esi": "0x00000004",
                "esp": "0x0025e8cc",
            },
            "trust": "context",
        },
        {
            "frame": 1,
            "function": "<name omitted>",
            "function_offset": "0xff",
            "module": "KERNELBASE.dll",
            "module_offset": "0x115f6",
            "offset": "0x775e15f6",
            "trust": "cfi",
        },
        {
            "frame": 2,
            "function": "IPC::ParamTraits<mozilla::net::NetAddr>::Write",
            "function_offset": "0x8d",
            "module": "kernel32.dll",
            "module_offset": "0x119f7",
            "offset": "0x766119f7",
            "trust": "cfi",
        },
        {
            "frame": 3,
            "function": "RealMsgWaitForMultipleObjectsEx(void **fakeargs)",
            "function_offset": "0xe1",
            "module": "user32.dll",
            "module_offset": "0x20869",
            "offset": "0x77370869",
            "trust": "cfi",
        },
        {
            "frame": 4,
            "function": "MsgWaitForMultipleObjects",
            "function_offset": "0x1e",
            "module": "user32.dll",
            "module_offset": "0x20b68",
            "offset": "0x77370b68",
            "trust": "cfi",
        },
        {
            "file": "F117835525________________________________________",
            "frame": 5,
            "function": "F_1152915508__________________________________",
            "function_offset": "0xbb",
            "line": 118,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x36a13b",
            "offset": "0x5e3aa13b",
            "trust": "cfi",
        },
        {
            "file": "F_851861807_______________________________________",
            "frame": 6,
            "function": "F2166389______________________________________",
            "function_offset": "0xe5",
            "line": 552,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x35faf5",
            "offset": "0x5e39faf5",
            "trust": "cfi",
        },
        {
            "file": "F_851861807_______________________________________",
            "frame": 7,
            "function": "F_917831355___________________________________",
            "function_offset": "0x29b",
            "line": 488,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x360a7b",
            "offset": "0x5e3a0a7b",
            "trust": "cfi",
        },
        {
            "file": "F_851861807_______________________________________",
            "frame": 8,
            "function": "F1315696776________________________________",
            "function_offset": "0xd",
            "line": 439,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x35e2fd",
            "offset": "0x5e39e2fd",
            "trust": "cfi",
        },
        {
            "file": "F_766591945_______________________________________",
            "frame": 9,
            "function": "F_1428703866________________________________",
            "function_offset": "0xc1",
            "line": 203,
            "module": "NPSWF32_14_0_0_125.dll",
            "module_offset": "0x35bf21",
            "offset": "0x5e39bf21",
            "trust": "cfi",
        },
    ],
    "threads_index": 0,
    "total_frames": 32,
}


class TestSignatureGenerationRule:
    def test_create_frame_list(self):
        sgr = rules.SignatureGenerationRule()
        frame_signatures_list = sgr._create_frame_list(FRAMES_FROM_JSON_DUMP)
        expected = [
            "NtWaitForMultipleObjects",
            "WaitForMultipleObjectsEx",
            "WaitForMultipleObjectsExImplementation",
            "RealMsgWaitForMultipleObjectsEx",
            "MsgWaitForMultipleObjects",
            "F_1152915508__________________________________",
            "F2166389______________________________________",
            "F_917831355___________________________________",
            "F1315696776________________________________",
            "F_1428703866________________________________",
        ]
        assert frame_signatures_list == expected

    def test_no_mutation(self):
        sgr = rules.SignatureGenerationRule()
        frames = {
            "frames": [
                {
                    "frame": 0,
                    "function": "NtWaitForMultipleObjects",
                    "function_offset": "0x15",
                    "module": "ntdll.dll",
                    "module_offset": "0x2015d",
                    "offset": "0x77ad015d",
                    "trust": "context",
                },
                {
                    "frame": 1,
                    "function": "WaitForMultipleObjectsEx",
                    "function_offset": "0xff",
                    "module": "KERNELBASE.dll",
                    "module_offset": "0x115f6",
                    "offset": "0x775e15f6",
                    "trust": "cfi",
                },
            ]
        }
        frames_copy = copy.deepcopy(frames)
        sgr._create_frame_list(frames_copy)

        # If they're the same, then there was no mutation
        assert frames == frames_copy

    def test_java_stack_trace(self):
        sgr = rules.SignatureGenerationRule()

        crash_data = {
            "java_stack_trace": (
                "   SomeJavaException: %s  \nat org.mozilla.lars.myInvention(larsFile.java)"
                % ("t" * 1000)
            )
        }

        result = generator.Result()

        # the call to be tested
        assert sgr.action(crash_data, result) is True

        expected = "SomeJavaException: at org.mozilla.lars.myInvention(larsFile.java)"
        assert result.signature == expected
        assert "proto_signature" not in result.extra
        assert result.notes == [
            "SignatureGenerationRule: JavaSignatureTool: dropped Java exception description due to length"  # noqa
        ]

    def test_c_stack_trace(self):
        sgr = rules.SignatureGenerationRule()

        crash_data = {"os": "Windows NT", "threads": [FRAMES_FROM_JSON_DUMP]}
        result = generator.Result()

        # the call to be tested
        assert sgr.action(crash_data, result) is True

        expected = (
            "MsgWaitForMultipleObjects | F_1152915508__________________________________"
        )
        assert result.signature == expected

        expected = (
            "NtWaitForMultipleObjects | WaitForMultipleObjectsEx | "
            "WaitForMultipleObjectsExImplementation | "
            "RealMsgWaitForMultipleObjectsEx | MsgWaitForMultipleObjects | "
            "F_1152915508__________________________________ | "
            "F2166389______________________________________ | "
            "F_917831355___________________________________ | "
            "F1315696776________________________________ | "
            "F_1428703866________________________________"
        )
        assert result.extra["proto_signature"] == expected
        assert result.notes == []

    def test_action_2_with_templates(self):
        sgr = rules.SignatureGenerationRule()

        crash_data = {
            "os": "Windows NT",
            "crashing_thread": 0,
            "threads": [FRAMES_FROM_JSON_DUMP_WITH_TEMPLATES],
        }
        result = generator.Result()

        # the call to be tested
        assert sgr.action(crash_data, result) is True

        assert result.signature == "Alpha<T>::Echo<T>"
        expected = (
            "NtWaitForMultipleObjects | Alpha<T>::Echo<T> | "
            "WaitForMultipleObjectsExImplementation | "
            "RealMsgWaitForMultipleObjectsEx | "
            "MsgWaitForMultipleObjects | "
            "F_1152915508__________________________________ | "
            "F2166389______________________________________ | "
            "F_917831355___________________________________ | "
            "F1315696776________________________________ | "
            "F_1428703866________________________________"
        )
        assert result.extra["proto_signature"] == expected
        assert result.notes == []

    def test_action_2_with_templates_and_special_case(self):
        sgr = rules.SignatureGenerationRule()

        crash_data = {
            "os": "Windows NT",
            "crashing_thread": 0,
            "threads": [FRAMES_FROM_JSON_DUMP_WITH_TEMPLATES_AND_SPECIAL_CASE],
        }
        result = generator.Result()

        # the call to be tested
        assert sgr.action(crash_data, result) is True

        assert (
            result.signature
            == "<name omitted> | IPC::ParamTraits<mozilla::net::NetAddr>::Write"
        )
        expected = (
            "NtWaitForMultipleObjects | "
            "<name omitted> | "
            "IPC::ParamTraits<mozilla::net::NetAddr>::Write | "
            "RealMsgWaitForMultipleObjectsEx | "
            "MsgWaitForMultipleObjects | "
            "F_1152915508__________________________________ | "
            "F2166389______________________________________ | "
            "F_917831355___________________________________ | "
            "F1315696776________________________________ | "
            "F_1428703866________________________________"
        )
        assert result.extra["proto_signature"] == expected
        assert result.notes == []

    def test_action_3(self):
        sgr = rules.SignatureGenerationRule()

        crash_data = {"thread": [[]]}
        result = generator.Result()

        # the call to be tested
        assert sgr.action(crash_data, result) is True

        assert result.signature == "EMPTY: no crashing thread identified"
        assert "proto_signature" not in result.extra
        assert result.notes == [
            "SignatureGenerationRule: CSignatureTool: No signature could be created because we do not know which thread crashed"  # noqa
        ]

    def test_lower_case_modules(self):
        sgr = rules.SignatureGenerationRule()

        crash_data = {
            "os": "Windows NT",
            "threads": [
                {
                    "frames": [
                        {"offset": "0x5e39bf21", "trust": "cfi"},
                        {"offset": "0x5e39bf21", "trust": "cfi"},
                        {"offset": "0x5e39bf21", "trust": "cfi"},
                        {
                            "frame": 3,
                            "module": "USER2.dll",
                            "module_offset": "0x20869",
                            "offset": "0x77370869",
                            "trust": "cfi",
                        },
                    ]
                }
            ],
        }
        result = generator.Result()

        # the call to be tested
        assert sgr.action(crash_data, result) is True
        assert result.signature == "user2.dll"
        expected = "@0x5e39bf21 | @0x5e39bf21 | @0x5e39bf21 | user2.dll@0x20869"
        assert result.extra["proto_signature"] == expected
        assert result.notes == []


class TestOOMSignature:
    def test_predicate_no_match(self):
        result = generator.Result()
        result.signature = "hello"
        rule = rules.OOMSignature()
        assert rule.predicate({}, result) is False

    def test_predicate(self):
        crash_data = {"oom_allocation_size": 17}
        result = {"signature": "hello", "notes": []}
        rule = rules.OOMSignature()
        assert rule.predicate(crash_data, result) is True

    def test_predicate_signature_fragment_1(self):
        crash_data = {}
        result = generator.Result()
        result.signature = "this | is | a | NS_ABORT_OOM | signature"
        rule = rules.OOMSignature()
        assert rule.predicate(crash_data, result) is True

    def test_predicate_signature_fragment_2(self):
        crash_data = {}
        result = generator.Result()
        result.signature = "mozalloc_handle_oom | this | is | bad"
        rule = rules.OOMSignature()
        assert rule.predicate(crash_data, result) is True

    def test_predicate_signature_fragment_3(self):
        crash_data = {}
        result = generator.Result()
        result.signature = "CrashAtUnhandlableOOM"
        rule = rules.OOMSignature()
        assert rule.predicate(crash_data, result) is True

    def test_action_success(self):
        crash_data = {}
        result = generator.Result()
        result.signature = "hello"
        rule = rules.OOMSignature()
        action_result = rule.action(crash_data, result)

        assert action_result is True
        assert result.signature == "OOM | unknown | hello"

    def test_action_small(self):
        crash_data = {"oom_allocation_size": 17}
        result = generator.Result()
        result.signature = "hello"
        rule = rules.OOMSignature()
        action_result = rule.action(crash_data, result)

        assert action_result is True
        assert result.signature == "OOM | small"

    def test_action_large(self):
        crash_data = {"oom_allocation_size": 17000000}
        result = generator.Result()
        result.signature = "hello"

        rule = rules.OOMSignature()
        action_result = rule.action(crash_data, result)

        assert action_result is True
        assert result.signature == "OOM | large | hello"


class TestAbortSignature:
    def test_predicate(self):
        rule = rules.AbortSignature()
        crash_data = {"abort_message": "something"}
        result = generator.Result()
        result.signature = "hello"
        assert rule.predicate(crash_data, result) is True

    def test_predicate_no_match(self):
        rule = rules.AbortSignature()
        # No AbortMessage
        crash_data = {}
        result = generator.Result()
        result.signature = "hello"
        assert rule.predicate(crash_data, result) is False

    def test_predicate_empty_message(self):
        rule = rules.AbortSignature()
        crash_data = {"abort_message": ""}
        result = generator.Result()
        result.signature = "hello"
        assert rule.predicate(crash_data, result) is False

    def test_action_success(self):
        rule = rules.AbortSignature()
        crash_data = {"abort_message": "unknown"}
        result = generator.Result()
        result.signature = "hello"
        action_result = rule.action(crash_data, result)
        assert action_result is True
        assert result.signature == "Abort | unknown | hello"

    def test_action_success_long_message(self):
        rule = rules.AbortSignature()

        crash_data = {"abort_message": "a" * 81}
        result = generator.Result()
        result.signature = "hello"
        action_result = rule.action(crash_data, result)

        assert action_result is True
        assert result.signature == "Abort | {}... | hello".format("a" * 77)

    @pytest.mark.parametrize(
        "abort_msg, expected",
        [
            # Test with just the "ABOR" thing at the start
            ("[5392] ###!!! ABORT: foo bar line 42", "Abort | foo bar line 42 | hello"),
            # Test with a file name and line number
            (
                (
                    "[7616] ###!!! ABORT: unsafe destruction: file "
                    "c:/builds/moz2_slave/m-rel-w32-00000000000000000000/build/src/"
                    "dom/plugins/ipc/PluginModuleParent.cpp, line 777"
                ),
                "Abort | unsafe destruction | hello",
            ),
            # Test with a message that lacks interesting content.
            ("[204] ###!!! ABORT: file ?, ", "Abort | hello"),
            # Test with another message that lacks interesting content.
            (
                (
                    "[4648] ###!!! ABORT: file resource:///modules/sessionstore/"
                    "SessionStore.jsm, line 1459"
                ),
                "Abort | hello",
            ),
            # Test with "unable to find a usable font" case
            (
                "unable to find a usable font (\u5fae\u8f6f\u96c5\u9ed1)",
                "Abort | unable to find a usable font | hello",
            ),
        ],
    )
    def test_action_success_remove_unwanted_parts(self, abort_msg, expected):
        rule = rules.AbortSignature()

        crash_data = {"abort_message": abort_msg}
        result = generator.Result()
        result.signature = "hello"
        action_result = rule.action(crash_data, result)

        assert action_result is True
        assert result.signature == expected

    def test_action_non_ascii_abort_message(self):
        # Non-ascii characters are removed from abort messages
        rule = rules.AbortSignature()
        crash_data = {"abort_message": "\u018a unknown"}
        result = generator.Result()
        result.signature = "hello"
        action_result = rule.action(crash_data, result)
        assert action_result is True
        assert result.signature == "Abort | unknown | hello"


class TestSigFixWhitespace:
    @pytest.mark.parametrize(
        "signature, expected",
        [
            # Leading and trailing whitespace are removed
            ("all   good", "all good"),
            ("all   good     ", "all good"),
            ("    all   good  ", "all good"),
            # Non-space whitespace is converted to spaces
            ("all\tgood", "all good"),
            ("all\n\ngood", "all good"),
            # Multiple consecutive spaces are converted to a single space
            ("all   good", "all good"),
            ("all  |  good", "all | good"),
        ],
    )
    def test_whitespace_fixing(self, signature, expected):
        rule = rules.SigFixWhitespace()
        result = generator.Result()
        result.signature = signature
        action_result = rule.action({}, result)
        assert action_result is True
        assert result.signature == expected


class TestSigTruncate:
    def test_predicate_no_match(self):
        rule = rules.SigTruncate()
        result = generator.Result()
        result.signature = "0" * 100
        assert rule.predicate({}, result) is False

    def test_predicate(self):
        rule = rules.SigTruncate()
        result = generator.Result()
        result.signature = "9" * 256
        assert rule.predicate({}, result) is True

    def test_action_success(self):
        rule = rules.SigTruncate()
        result = generator.Result()
        result.signature = "9" * 256
        action_result = rule.action({}, result)
        assert action_result is True
        assert len(result.signature) == 255
        assert result.signature.endswith("9...")


class TestStackwalkerErrorSignatureRule:
    def test_predicate_no_match_signature(self):
        rule = rules.StackwalkerErrorSignatureRule()
        result = generator.Result()
        result.signature = "0" * 100
        assert rule.predicate({}, result) is False

    def test_predicate_no_match_missing_mdsw_status_string(self):
        rule = rules.StackwalkerErrorSignatureRule()
        result = generator.Result()
        result.signature = "EMPTY: like my soul"
        assert rule.predicate({}, result) is False

    def test_predicate(self):
        rule = rules.StackwalkerErrorSignatureRule()
        crash_data = {"mdsw_status_string": "catastrophic stackwalker failure"}
        result = generator.Result()
        result.signature = "EMPTY: like my soul"
        assert rule.predicate(crash_data, result) is True

    def test_action_success(self):
        rule = rules.StackwalkerErrorSignatureRule()
        crash_data = {"mdsw_status_string": "catastrophic stackwalker failure"}
        result = generator.Result()
        result.signature = "EMPTY: like my soul"
        action_result = rule.action(crash_data, result)
        assert action_result is True
        expected = "EMPTY: like my soul; catastrophic stackwalker failure"
        assert result.signature == expected


class TestSignatureWatchDogRule:
    def test_instantiation(self):
        srwd = rules.SignatureRunWatchDog()

        assert isinstance(srwd.c_signature_tool, rules.CSignatureTool)
        assert isinstance(srwd.java_signature_tool, rules.JavaSignatureTool)

        assert srwd._get_crashing_thread({}) == 0

    def test_predicate(self):
        srwd = rules.SignatureRunWatchDog()

        result = generator.Result()
        result.signature = "I'm not real"
        assert srwd.predicate({}, result) is False

        result = generator.Result()
        result.signature = "mozilla::`anonymous namespace''::RunWatchdog(void*)"
        assert srwd.predicate({}, result) is True

        result = generator.Result()
        result.signature = "mozilla::(anonymous namespace)::RunWatchdog"
        assert srwd.predicate({}, result) is True

    def test_action(self):
        sgr = rules.SignatureRunWatchDog()

        crash_data = {
            "os": "Windows NT",
            "crashing_thread": 0,
            "threads": [FRAMES_FROM_JSON_DUMP],
        }
        result = generator.Result()
        result.signature = "foo::bar"

        # the call to be tested
        assert sgr.action(crash_data, result) is True

        # Verify the signature has been re-generated based on thread 0.
        expected = (
            "shutdownhang | MsgWaitForMultipleObjects | "
            "F_1152915508__________________________________"
        )
        assert result.signature == expected
        assert result.notes == []


class TestSignatureJitCategory:
    def test_predicate_no_match(self):
        rule = rules.SignatureJitCategory()

        crash_data = {}
        result = {"signature": "", "notes": []}
        assert rule.predicate(crash_data, result) is False

        crash_data = {"jit_category": ""}
        result = {"signature": "", "notes": []}

        assert rule.predicate(crash_data, result) is False

    def test_predicate(self):
        rule = rules.SignatureJitCategory()

        crash_data = {"jit_category": "JIT Crash"}
        result = {"signature": "", "notes": []}

        assert rule.predicate(crash_data, result) is True

    def test_action_success(self):
        rule = rules.SignatureJitCategory()

        crash_data = {"jit_category": "JIT Crash"}
        result = generator.Result()
        result.signature = "foo::bar"

        action_result = rule.action(crash_data, result)
        assert action_result is True
        assert result.signature == "jit | JIT Crash"
        assert result.notes == [
            'SignatureJitCategory: Signature replaced with a JIT Crash Category, was: "foo::bar"'
        ]


class TestSignatureIPCChannelError:
    def test_predicate_no_match(self):
        rule = rules.SignatureIPCChannelError()

        result = generator.Result()
        assert rule.predicate({}, result) is False

        crash_data = {"ipc_channel_error": ""}
        result = {"signature": "", "notes": []}
        assert rule.predicate(crash_data, result) is False

    def test_predicate(self):
        rule = rules.SignatureIPCChannelError()

        crash_data = {"ipc_channel_error": "foo, bar"}
        result = generator.Result()
        assert rule.predicate(crash_data, result) is True

    def test_regular_ipcchannelerror(self):
        rule = rules.SignatureIPCChannelError()

        channel_error = "ipc" * 50
        original_signature = "foo::bar"

        crash_data = {"ipc_channel_error": channel_error}
        result = generator.Result()
        result.signature = original_signature

        action_result = rule.action(crash_data, result)
        assert action_result is True
        expected = "IPCError-content | {}".format(channel_error[:100])
        assert result.signature == expected
        assert result.notes == [
            "SignatureIPCChannelError: IPC Channel Error stomped on signature"
        ]

        # Now test with a browser crash.
        crash_data["additional_minidumps"] = "browser"
        result = generator.Result()
        result.signature = original_signature

        action_result = rule.action(crash_data, result)
        assert action_result is True

        assert result.signature == "IPCError-browser | {}".format(channel_error[:100])
        assert result.notes == [
            "SignatureIPCChannelError: IPC Channel Error stomped on signature"
        ]

    def test_shutdownkill(self):
        rule = rules.SignatureIPCChannelError()

        original_signature = "foo::bar"
        crash_data = {
            "ipc_channel_error": "ShutDownKill",
            "additional_minidumps": "browser",
        }
        result = generator.Result()
        result.signature = original_signature

        action_result = rule.action(crash_data, result)
        assert action_result is True

        assert result.signature == "IPCError-browser | ShutDownKill | {}".format(
            original_signature
        )
        assert result.notes == ["SignatureIPCChannelError: IPC Channel Error prepended"]


class TestSignatureShutdownTimeout:
    def test_predicate_no_match(self):
        rule = rules.SignatureShutdownTimeout()
        result = generator.Result()
        assert rule.predicate({}, result) is False

    def test_predicate(self):
        rule = rules.SignatureShutdownTimeout()

        crash_data = {"async_shutdown_timeout": '{"foo": "bar"}'}
        result = generator.Result()
        assert rule.predicate(crash_data, result) is True

    def test_action_missing_valueerror(self):
        rule = rules.SignatureShutdownTimeout()

        crash_data = {
            # This will cause json.load to raise an error
            "async_shutdown_timeout": "{{{{"
        }
        result = generator.Result()
        result.signature = "foo"

        action_result = rule.action(crash_data, result)
        assert action_result is True
        assert result.signature == "AsyncShutdownTimeout | UNKNOWN"

        assert "Error parsing AsyncShutdownTimeout:" in result.notes[0]
        assert "Expecting property name" in result.notes[0]
        print(result.notes[1])
        assert (
            'Signature replaced with a Shutdown Timeout signature, was: "foo"'
            in result.notes[1]
        )

    def test_action_missing_keyerror(self):
        rule = rules.SignatureShutdownTimeout()

        crash_data = {
            "async_shutdown_timeout": json.dumps({"no": "phase or condition"})
        }
        result = generator.Result()
        result.signature = "foo"

        action_result = rule.action(crash_data, result)
        assert action_result is True
        assert result.signature == "AsyncShutdownTimeout | UNKNOWN"

        assert result.notes == [
            "SignatureShutdownTimeout: Error parsing AsyncShutdownTimeout: 'phase'",
            'SignatureShutdownTimeout: Signature replaced with a Shutdown Timeout signature, was: "foo"',  # noqa
        ]

    def test_action_success(self):
        rule = rules.SignatureShutdownTimeout()

        crash_data = {
            "async_shutdown_timeout": json.dumps(
                {"phase": "beginning", "conditions": [{"name": "A"}, {"name": "B"}]}
            )
        }
        result = generator.Result()
        result.signature = "foo"

        action_result = rule.action(crash_data, result)
        assert action_result is True
        assert result.signature == "AsyncShutdownTimeout | beginning | A,B"
        assert result.notes == [
            'SignatureShutdownTimeout: Signature replaced with a Shutdown Timeout signature, was: "foo"'  # noqa
        ]

    def test_action_success_string_conditions(self):
        rule = rules.SignatureShutdownTimeout()

        crash_data = {
            "async_shutdown_timeout": json.dumps(
                {"phase": "beginning", "conditions": ["A", "B", "C"]}
            )
        }
        result = generator.Result()
        result.signature = "foo"

        action_result = rule.action(crash_data, result)
        assert action_result is True
        assert result.signature == "AsyncShutdownTimeout | beginning | A,B,C"
        assert result.notes == [
            'SignatureShutdownTimeout: Signature replaced with a Shutdown Timeout signature, was: "foo"'  # noqa
        ]

    def test_action_success_empty_conditions_key(self):
        rule = rules.SignatureShutdownTimeout()

        crash_data = {
            "async_shutdown_timeout": json.dumps(
                {"phase": "beginning", "conditions": []}
            )
        }
        result = generator.Result()
        result.signature = "foo"

        action_result = rule.action(crash_data, result)
        assert action_result is True
        assert result.signature == "AsyncShutdownTimeout | beginning | (none)"
        assert result.notes == [
            'SignatureShutdownTimeout: Signature replaced with a Shutdown Timeout signature, was: "foo"'  # noqa
        ]


class TestSignatureIPCMessageName:
    def test_predicate_no_ipc_message_name(self):
        rule = rules.SignatureIPCMessageName()
        result = generator.Result()
        assert rule.predicate({}, result) is False

    def test_predicate_empty_string(self):
        rule = rules.SignatureIPCMessageName()
        crash_data = {"ipc_message_name": ""}
        result = generator.Result()
        assert rule.predicate(crash_data, result) is False

    def test_predicate(self):
        rule = rules.SignatureIPCMessageName()
        crash_data = {"ipc_message_name": "foo, bar"}
        result = generator.Result()
        result.signature = "fooo::baar"
        assert rule.predicate(crash_data, result) is True

    def test_action_success(self):
        rule = rules.SignatureIPCMessageName()
        crash_data = {"ipc_message_name": "foo, bar"}
        result = generator.Result()
        result.signature = "fooo::baar"
        action_result = rule.action(crash_data, result)
        assert action_result is True
        assert result.signature == "fooo::baar | IPC_Message_Name=foo, bar"


class TestSignatureParentIDNotEqualsChildID:
    def test_predicate_no_moz_crash_reason(self):
        rule = rules.SignatureParentIDNotEqualsChildID()
        result = {"signature": "", "notes": []}
        assert rule.predicate({}, result) is False

    def test_predicate_empty_moz_crash_reason(self):
        rule = rules.SignatureParentIDNotEqualsChildID()
        crash_data = {"moz_crash_reason": ""}
        result = {"signature": "", "notes": []}
        assert rule.predicate(crash_data, result) is False

    def test_predicate_match(self):
        rule = rules.SignatureParentIDNotEqualsChildID()
        crash_data = {
            "moz_crash_reason": "MOZ_RELEASE_ASSERT(parentBuildID == childBuildID)"
        }
        result = generator.Result()
        result.signature = "fooo::baar"
        assert rule.predicate(crash_data, result) is True

    def test_action(self):
        rule = rules.SignatureParentIDNotEqualsChildID()
        crash_data = {
            "moz_crash_reason": "MOZ_RELEASE_ASSERT(parentBuildID == childBuildID)"
        }
        result = generator.Result()
        result.signature = "fooo::baar"
        action_result = rule.action(crash_data, result)
        assert action_result is True
        assert result.signature == "parentBuildID != childBuildID"
        assert result.notes == [
            'SignatureParentIDNotEqualsChildID: Signature replaced with MOZ_RELEASE_ASSERT, was: "fooo::baar"'  # noqa
        ]
