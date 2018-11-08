# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy

from configman.dotdict import DotDict

from socorro.lib.util import chunkify, dotdict_to_dict


def test_chunkify():
    # chunking nothing yields nothing.
    assert list(chunkify([], 1)) == []

    # chunking list where len(list) < n
    assert list(chunkify([1], 10)) == [(1,)]

    # chunking a list where len(list) == n
    assert list(chunkify([1, 2], 2)) == [(1, 2)]

    # chunking list where len(list) > n
    assert list(chunkify([1, 2, 3, 4, 5], 2)) == [(1, 2), (3, 4), (5,)]


class Testdotdict_to_dict(object):
    def test_primitives(self):
        # Test all the primitives
        assert dotdict_to_dict(None) is None
        assert dotdict_to_dict([]) == []
        assert dotdict_to_dict('') == ''
        assert dotdict_to_dict(1) == 1
        assert dotdict_to_dict({}) == {}

    def test_complex(self):
        def comp(data, expected):
            # First dotdict_to_dict the data and compare it.
            new_dict = dotdict_to_dict(data)
            assert new_dict == expected

            # Now deepcopy the new dict to make sure it's ok.
            copy.deepcopy(new_dict)

        # dict -> dict
        comp({'a': 1}, {'a': 1})

        # outer dotdict -> dict
        comp(DotDict({'a': 1}), {'a': 1})

        # in a list
        comp(
            {
                'a': 1,
                'b': [
                    DotDict({
                        'a': 2
                    }),
                    3,
                    4
                ]
            },
            {'a': 1, 'b': [{'a': 2}, 3, 4]}
        )
        # mixed dotdicts
        comp(
            DotDict({
                'a': 1,
                'b': DotDict({
                    'a': 2
                })
            }),
            {'a': 1, 'b': {'a': 2}}
        )
