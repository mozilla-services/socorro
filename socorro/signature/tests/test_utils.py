# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from ..utils import collapse, drop_bad_characters, parse_source_file


@pytest.mark.parametrize('text, expected', [
    ('', ''),
    (u'', ''),

    ('123', '123'),
    (u'123', '123'),

    # Drop non-ascii characters
    ('1\xc6\x8a23', '123'),
    (u'1\u018a23', '123'),

    # Drop non-space whitespace characters
    ('\r\n\t1 23', '1 23'),
    (u'\r\n\t1 23', '1 23'),

    # Drop non-printable characters
    ('\0\b1 23', '1 23'),
    (u'\0\b1 23', '1 23'),
])
def test_drop_bad_characters(text, expected):
    assert drop_bad_characters(text) == expected


@pytest.mark.parametrize('source_file, expected', [
    (
        'hg:hg.mozilla.org/releases/mozilla-release:js/src/vm/JSFunction.cpp:7d280b7e277b82ef282325fefb601c10698e075b',  # noqa
        'js/src/vm/JSFunction.cpp'
    ),
    (
        'git:github.com/rust-lang/rust:src/libcore/cmp.rs:4d90ac38c0b61bb69470b61ea2cccea0df48d9e5',  # noqa
        'src/libcore/cmp.rs'
    ),
    (
        'f:\dd\vctools\crt\crtw32\mbstring\mbsnbico.c',
        '\dd\vctools\crt\crtw32\mbstring\mbsnbico.c'
    ),
    (
        'd:\w7rtm\com\rpc\ndrole\udt.cxx',
        '\w7rtm\com\rpc\ndrole\udt.cxx'
    ),
    (
        '/build/firefox-Kq_6Wg/firefox-54.0+build3/memory/mozjemalloc/jemalloc.c',
        '/build/firefox-Kq_6Wg/firefox-54.0+build3/memory/mozjemalloc/jemalloc.c'
    ),
    (
        None,
        None
    ),
])
def test_parse_source_file(source_file, expected):
    assert parse_source_file(source_file) == expected


@pytest.mark.parametrize('function, expected', [
    ('', ''),

    # Test parsing variations
    ('HeapFree', 'HeapFree'),
    ('Foo<bar>', 'Foo<T>'),
    ('<bar>Foo', '<T>Foo'),
    ('<bar>', '<T>'),
    ('Foo<bar', 'Foo<T>'),
    ('Foo<bar <baz> >', 'Foo<T>'),
    ('Foo<bar<baz>', 'Foo<T>'),

    (
        'CLayeredObjectWithCLS<CCryptoSession>::Release()',
        'CLayeredObjectWithCLS<T>::Release()'
    ),
    (
        'core::ptr::drop_in_place<style::stylist::CascadeData>',
        'core::ptr::drop_in_place<T>'
    ),

    # Test exceptions
    (
        '<rayon_core::job::HeapJob<BODY> as rayon_core::job::Job>::execute',
        '<rayon_core::job::HeapJob<BODY> as rayon_core::job::Job>::execute'
    ),
    (
        '<name omitted>',
        '<name omitted>'
    ),
    (
        'IPC::ParamTraits<nsTSubstring<char> >::Write(IPC::Message *,nsTSubstring<char> const &)',
        'IPC::ParamTraits<nsTSubstring<T> >::Write(IPC::Message *,nsTSubstring<T> const &)'
    ),
])
def test_collapse(function, expected):
    params = {
        'function': function,
        'open_string': '<',
        'close_string': '>',
        'replacement': '<T>',
        'exceptions': ['name omitted', 'IPC::ParamTraits', ' as ']
    }
    assert collapse(**params) == expected
