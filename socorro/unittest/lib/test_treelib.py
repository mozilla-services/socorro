# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from socorro.lib import treelib


class TestParsePath:
    @pytest.mark.parametrize('path, expected', [
        # Keys
        ('a', [('key', 'a')]),
        ('a.b', [('key', 'a'), ('key', 'b')]),

        # Indexes
        ('a.[1]', [('key', 'a'), ('index', 1)]),
        ('a.[10]', [('key', 'a'), ('index', 10)]),
        ('a.[-1]', [('key', 'a'), ('index', -1)]),

        # Multi
        ('a.[1].b', [('key', 'a'), ('index', 1), ('key', 'b')]),
    ])
    def test_good_paths(self, path, expected):
        assert treelib.parse_path(path) == expected

    def test_empty_path(self):
        with pytest.raises(treelib.MalformedPath) as exc_info:
            treelib.parse_path('')

        exc_str = str(exc_info.exconly())
        expected = "MalformedPath: '' is a malformed path: empty edge"
        assert exc_str == expected

    def test_bad_path_empty_edge(self):
        with pytest.raises(treelib.MalformedPath) as exc_info:
            treelib.parse_path('a..b')

        exc_str = str(exc_info.exconly())
        expected = "MalformedPath: 'a..b' is a malformed path: empty edge"
        assert exc_str == expected

    def test_bad_path_mismatched_brackets(self):
        with pytest.raises(treelib.MalformedPath) as exc_info:
            treelib.parse_path('a.[10')

        exc_str = str(exc_info.exconly())
        expected = "MalformedPath: 'a.[10' is a malformed path: [ without ]"
        assert exc_str == expected

    def test_bad_path_index_is_not_int(self):
        with pytest.raises(treelib.MalformedPath) as exc_info:
            treelib.parse_path('a.[a]')

        exc_str = str(exc_info.exconly())
        expected = (
            "MalformedPath: 'a.[a]' is a malformed path: "
            "invalid literal for int() with base 10: 'a'"
        )
        assert exc_str == expected


class TestTreeGet:
    @pytest.mark.parametrize('tree, path, expected', [
        # Key paths
        ({'a': 1}, 'a', 1),
        ({'a': {'b': 1}}, 'a.b', 1),

        # Index paths
        ({'a': [1]}, 'a.[0]', 1),
        ({'a': [1, 2, 3]}, 'a.[-1]', 3),
        ({'a': [{'b': 1}]}, 'a.[0].b', 1)
    ])
    def test_good_gets(self, tree, path, expected):
        assert treelib.tree_get(tree, path) == expected

    def test_edge_missing(self):
        tree = {'a': 1}
        with pytest.raises(KeyError) as exc_info:
            assert treelib.tree_get(tree, 'b')

        exc_str = str(exc_info.exconly())
        assert exc_str == 'KeyError: \'b\''

    def test_index_missing(self):
        tree = {'a': []}
        with pytest.raises(IndexError) as exc_info:
            assert treelib.tree_get(tree, 'a.[1]')

        exc_str = str(exc_info.exconly())
        assert exc_str == 'IndexError: list index out of range'

    def test_default(self):
        tree = {'a': 1}
        assert treelib.tree_get(tree, 'b', default=10) == 10
        assert treelib.tree_get(tree, 'b.c.d', default=10) == 10

        tree = {'a': []}
        assert treelib.tree_get(tree, 'a.[1]', default=10) == 10
        assert treelib.tree_get(tree, 'a.[1].b.c.d', default=10) == 10
