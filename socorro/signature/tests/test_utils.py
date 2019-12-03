# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from ..utils import (
    collapse,
    drop_bad_characters,
    drop_prefix_and_return_type,
    parse_crashid,
    parse_source_file,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", ""),
        ("", ""),
        ("123", "123"),
        ("123", "123"),
        # Drop non-ascii characters
        ("1\xc6\x8a23", "123"),
        ("1\u018a23", "123"),
        # Drop non-space whitespace characters
        ("\r\n\t1 23", "1 23"),
        ("\r\n\t1 23", "1 23"),
        # Drop non-printable characters
        ("\0\b1 23", "1 23"),
        ("\0\b1 23", "1 23"),
    ],
)
def test_drop_bad_characters(text, expected):
    assert drop_bad_characters(text) == expected


@pytest.mark.parametrize(
    "source_file, expected",
    [
        (
            "hg:hg.mozilla.org/releases/mozilla-release:js/src/vm/JSFunction.cpp:7d280b7e277b82ef282325fefb601c10698e075b",  # noqa
            "js/src/vm/JSFunction.cpp",
        ),
        (
            "git:github.com/rust-lang/rust:src/libcore/cmp.rs:4d90ac38c0b61bb69470b61ea2cccea0df48d9e5",  # noqa
            "src/libcore/cmp.rs",
        ),
        (
            "f:\\dd\\vctools\\crt\\crtw32\\mbstring\\mbsnbico.c",
            "\\dd\\vctools\\crt\\crtw32\\mbstring\\mbsnbico.c",
        ),
        ("d:\\w7rtm\\com\\rpc\\ndrole\\udt.cxx", "\\w7rtm\\com\\rpc\\ndrole\\udt.cxx"),
        (
            "/build/firefox-Kq_6Wg/firefox-54.0+build3/memory/mozjemalloc/jemalloc.c",
            "/build/firefox-Kq_6Wg/firefox-54.0+build3/memory/mozjemalloc/jemalloc.c",
        ),
        (None, None),
    ],
)
def test_parse_source_file(source_file, expected):
    assert parse_source_file(source_file) == expected


@pytest.mark.parametrize(
    "function, expected",
    [
        ("", ""),
        # Test parsing variations
        ("HeapFree", "HeapFree"),
        ("Foo<bar>", "Foo<T>"),
        ("<bar>Foo", "<T>Foo"),
        ("<bar>", "<T>"),
        ("Foo<bar", "Foo<T>"),
        ("Foo<bar <baz> >", "Foo<T>"),
        ("Foo<bar<baz>", "Foo<T>"),
        (
            "CLayeredObjectWithCLS<CCryptoSession>::Release()",
            "CLayeredObjectWithCLS<T>::Release()",
        ),
        (
            "core::ptr::drop_in_place<style::stylist::CascadeData>",
            "core::ptr::drop_in_place<T>",
        ),
        # Test exceptions
        (
            "<rayon_core::job::HeapJob<BODY> as rayon_core::job::Job>::execute",
            "<rayon_core::job::HeapJob<BODY> as rayon_core::job::Job>::execute",
        ),
        ("<name omitted>", "<name omitted>"),
        (
            "IPC::ParamTraits<nsTSubstring<char> >::Write(IPC::Message *,nsTSubstring<char> const &)",
            "IPC::ParamTraits<nsTSubstring<T> >::Write(IPC::Message *,nsTSubstring<T> const &)",
        ),
    ],
)
def test_collapse(function, expected):
    params = {
        "function": function,
        "open_string": "<",
        "close_string": ">",
        "replacement": "<T>",
        "exceptions": ["name omitted", "IPC::ParamTraits", " as "],
    }
    assert collapse(**params) == expected


@pytest.mark.parametrize(
    "function, expected",
    [
        # C/C++
        ("`anonymous namespace'::xClose", "`anonymous namespace'::xClose"),
        (
            "bool CCGraphBuilder::BuildGraph(class js::SliceBudget & const)",
            "CCGraphBuilder::BuildGraph(class js::SliceBudget & const)",
        ),
        (
            "int nsHtml5Tokenizer::stateLoop<nsHtml5SilentPolicy>(int, char16_t, int, char16_t*, bool, int, int)",  # noqa
            "nsHtml5Tokenizer::stateLoop<nsHtml5SilentPolicy>(int, char16_t, int, char16_t*, bool, int, int)",  # noqa
        ),
        (
            "js::ObjectGroup* DoCallback<js::ObjectGroup*>(JS::CallbackTracer*, js::ObjectGroup**, char const*)",  # noqa
            "DoCallback<js::ObjectGroup*>(JS::CallbackTracer*, js::ObjectGroup**, char const*)",
        ),
        (
            "js::Shape* js::Allocate<js::Shape, (js::AllowGC)1>(JSContext*)",
            "js::Allocate<js::Shape, (js::AllowGC)1>(JSContext*)",
        ),
        (
            "long sandbox::TargetNtCreateFile( *, void * *, unsigned long, struct _OBJECT_ATTRIBUTES *, struct _IO_STATUS_BLOCK *, union _LARGE_INTEGER *, unsigned long, unsigned long, unsigned long, unsigned long, void *, unsigned long)",  # noqa
            "sandbox::TargetNtCreateFile( *, void * *, unsigned long, struct _OBJECT_ATTRIBUTES *, struct _IO_STATUS_BLOCK *, union _LARGE_INTEGER *, unsigned long, unsigned long, unsigned long, unsigned long, void *, unsigned long)",  # noqa
        ),
        (
            "static `anonymous-namespace'::reflectStatus `anonymous namespace'::internal_ReflectHistogramAndSamples(struct JSContext *, class JS::Handle<JSObject *>, class base::Histogram *, const class base::Histogram::SampleSet & const)",  # noqa
            "`anonymous namespace'::internal_ReflectHistogramAndSamples(struct JSContext *, class JS::Handle<JSObject *>, class base::Histogram *, const class base::Histogram::SampleSet & const)",  # noqa
        ),
        (
            "static bool `anonymous namespace'::TypeAnalyzer::specializePhis()",
            "`anonymous namespace'::TypeAnalyzer::specializePhis()",
        ),
        (
            "static char * dtoa(struct DtoaState *, union U, int, int, int *, int *, char * *)",
            "dtoa(struct DtoaState *, union U, int, int, int *, int *, char * *)",
        ),
        (
            "static class js::HashSet<js::Shape *,js::ShapeHasher,js::SystemAllocPolicy> * HashChildren(class js::Shape *, class js::Shape *)",  # noqa
            "HashChildren(class js::Shape *, class js::Shape *)",
        ),
        (
            "static class mozilla::dom::Element * GetPropagatedScrollbarStylesForViewport(class nsPresContext *, struct mozilla::ScrollbarStyles *)",  # noqa
            "GetPropagatedScrollbarStylesForViewport(class nsPresContext *, struct mozilla::ScrollbarStyles *)",  # noqa
        ),
        (
            "static const class SkTMaskGamma<3,3,3> & const cached_mask_gamma(float, float, float)",
            "cached_mask_gamma(float, float, float)",
        ),
        (
            "static short ssl_Poll(struct PRFileDesc *, short, short *)",
            "ssl_Poll(struct PRFileDesc *, short, short *)",
        ),
        (
            "static struct already_AddRefed<nsIAsyncShutdownClient> `anonymous namespace'::GetShutdownPhase()",  # noqa
            "`anonymous namespace'::GetShutdownPhase()",
        ),
        (
            "static struct Index * sqlite3FindIndex(struct sqlite3 *, const char *, const char *)",
            "sqlite3FindIndex(struct sqlite3 *, const char *, const char *)",
        ),
        ("static unsigned int pr_root(void *)", "pr_root(void *)"),
        (
            "static void * Allocator<MozJemallocBase>::malloc(unsigned __int64)",
            "Allocator<MozJemallocBase>::malloc(unsigned __int64)",
        ),
        (
            "static void * * NewUNumberFormat(struct JSContext *, class JS::Handle<js::NumberFormatObject *>)",  # noqa
            "NewUNumberFormat(struct JSContext *, class JS::Handle<js::NumberFormatObject *>)",
        ),
        (
            "void mozilla::layers::MLGDeviceD3D11::~MLGDeviceD3D11()",
            "mozilla::layers::MLGDeviceD3D11::~MLGDeviceD3D11()",
        ),
        (
            "void * arena_t::MallocSmall(unsigned int, bool)",
            "arena_t::MallocSmall(unsigned int, bool)",
        ),
        # Rust
        (
            "bool prefs_parser::prefs_parser_parse(char *, prefs_parser::PrefValueKind, char *, unsigned __int64,  *,  *)",  # noqa
            "prefs_parser::prefs_parser_parse(char *, prefs_parser::PrefValueKind, char *, unsigned __int64,  *,  *)",  # noqa
        ),
        (
            "float geckoservo::glue::Servo_AnimationValue_GetOpacity(struct style::gecko_bindings::structs::root::RawServoAnimationValue *)",  # noqa
            "geckoservo::glue::Servo_AnimationValue_GetOpacity(struct style::gecko_bindings::structs::root::RawServoAnimationValue *)",  # noqa
        ),
        (
            "static <NoType> std::panicking::begin_panic<str*>(struct str*, struct (str*, u32, u32) *)",
            "std::panicking::begin_panic<str*>(struct str*, struct (str*, u32, u32) *)",
        ),
        (
            "static core::result::Result style::properties::PropertyDeclaration::to_css(struct nsstring::nsAString *)",  # noqa
            "style::properties::PropertyDeclaration::to_css(struct nsstring::nsAString *)",
        ),
        (
            "static struct atomic_refcell::AtomicRefMut<style::data::ElementData> style::gecko::wrapper::{{impl}}::ensure_data(struct style::gecko::wrapper::GeckoElement *)",  # noqa
            "style::gecko::wrapper::{{impl}}::ensure_data(struct style::gecko::wrapper::GeckoElement *)",
        ),
        (
            "static union core::option::Option<usize> encoding_rs::Encoder::max_buffer_length_from_utf16_without_replacement(unsigned __int64)",  # noqa
            "encoding_rs::Encoder::max_buffer_length_from_utf16_without_replacement(unsigned __int64)",
        ),
        (
            "static unsigned __int64 style::gecko::pseudo_element::PseudoElement::index()",
            "style::gecko::pseudo_element::PseudoElement::index()",
        ),
        (
            "static void alloc::boxed::{{impl}}::call_box<(),closure>(struct closure *, <NoType>)",
            "alloc::boxed::{{impl}}::call_box<(),closure>(struct closure *, <NoType>)",
        ),
        ("static void core::option::expect_failed()", "core::option::expect_failed()"),
        (
            "struct style::gecko_bindings::sugar::ownership::Strong<style::gecko_bindings::structs::root::RawServoStyleSheetContents> geckoservo::glue::Servo_StyleSheet_Empty(style::gecko_bindings::structs::root::mozilla::css::SheetParsingMode)",  # noqa
            "geckoservo::glue::Servo_StyleSheet_Empty(style::gecko_bindings::structs::root::mozilla::css::SheetParsingMode)",  # noqa
        ),
        (
            "unsigned int encoding_glue::mozilla_encoding_encode_from_utf16(struct encoding_rs::Encoding * *, unsigned short *, unsigned int, struct nsstring::nsACString *)",  # noqa
            "encoding_glue::mozilla_encoding_encode_from_utf16(struct encoding_rs::Encoding * *, unsigned short *, unsigned int, struct nsstring::nsACString *)",  # noqa
        ),
        (
            "void geckoservo::glue::Servo_MaybeGCRuleTree(struct style::gecko_bindings::bindings::RawServoStyleSet *)",  # noqa
            "geckoservo::glue::Servo_MaybeGCRuleTree(struct style::gecko_bindings::bindings::RawServoStyleSet *)",  # noqa
        ),
        # Handle whitespace between function and parenthesized arguments and [clone .cold.xxx] correctly
        (
            "[thunk]:CShellItem::QueryInterface`adjustor{12}' (_GUID const&, void**)",
            "[thunk]:CShellItem::QueryInterface`adjustor{12}' (_GUID const&, void**)",
        ),
        (
            "nsXPConnect::InitStatics() [clone .cold.638]",
            "nsXPConnect::InitStatics() [clone .cold.638]",
        ),
        (
            "js::AssertObjectIsSavedFrameOrWrapper(JSContext*, JS::Handle<JSObject*>) [clone .isra.234] [clone .cold.687]",  # noqa
            "js::AssertObjectIsSavedFrameOrWrapper(JSContext*, JS::Handle<JSObject*>) [clone .isra.234] [clone .cold.687]",  # noqa
        ),
        # Handle an aberrant case
        (
            "(anonymous namespace)::EnqueueTask(already_AddRefed<nsIRunnable>, int)",
            "(anonymous namespace)::EnqueueTask(already_AddRefed<nsIRunnable>, int)",
        ),
    ],
)
def test_drop_prefix_and_return_type(function, expected):
    assert drop_prefix_and_return_type(function) == expected


@pytest.mark.parametrize(
    "item, expected",
    [
        ("", None),
        ("foo", None),
        (
            "0b794045-87ec-4649-9ce1-73ec10191120",
            "0b794045-87ec-4649-9ce1-73ec10191120",
        ),
        (
            "bp-0b794045-87ec-4649-9ce1-73ec10191120",
            "0b794045-87ec-4649-9ce1-73ec10191120",
        ),
        (
            "https://crash-stats.mozilla.org/report/index/0b794045-87ec-4649-9ce1-73ec10191120",
            "0b794045-87ec-4649-9ce1-73ec10191120",
        ),
    ],
)
def test_parse_crashid(item, expected):
    assert parse_crashid(item) == expected
