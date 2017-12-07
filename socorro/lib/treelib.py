# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Library for manipulating trees in Python made up of dicts and lists.


Goals
=====

The primary goal of this library is to make it less unwieldy to manipulate trees
made up of Python dicts and lists.

For example, say we want to get a value deep in the tree. we could do this::

  value = tree['a']['b']['c']


That'll throw a ``KeyError`` if any of those bits are missing. So you could
handle that::

  try:
      value = tree['a']['b']['c']
  except KeyError:
      value = None


Alternatively, you could do this::

  value = tree.get('a', {}).get('b', {}).get('c': None)


These work, but both are unwieldy and not very readable.

This library aims to make sane use cases for tree manipulation easier to read
and think about.


Paths
=====

A path is a string specifying a period-delimited list of edges. Edges can be:

1. a key (for a dict)
2. an index (for a list)

Example paths::

  a
  a.[10].foo_bar.Bar
  a.b.[-1].Bar


Paths can be composed using string operations since they're just strings.


Key
---

Keys are identifiers that are:

1. composed entirely of ascii alphanumeric characters, hyphens, and underscores
2. at least one character long

For example, these are all valid keys::

  a
  foo
  FooBar
  Foo-Bar
  foo_bar


Index
-----

Indexes indicate a 0-based list index. They are:

1. integers
2. wrapped in ``[`` and ``]``
3. can be negative

For example, these are all valid indexes::

  [0]
  [1]
  [-50]

"""

INDEX_EDGE = 'index'
KEY_EDGE = 'key'
NO_DEFAULT = object()


class MalformedPath(Exception):
    pass


def parse_path(path):
    """Takes a path and splits it into parts

    :arg str path: period delimited path of edges

    :returns: tokenized path

    :raises MalformedPath: if the path is malformed

    """
    # Split path into parts on period
    parts = [part.strip() for part in path.split('.')]

    # Convert parts to tokens by checking for [ and ]
    tokens = []
    for part in parts:
        if not part:
            raise MalformedPath('%r is a malformed path: empty edge' % path)

        if part[0] == '[':
            if part[-1] != ']':
                raise MalformedPath('%r is a malformed path: [ without ]' % path)
            try:
                tokens.append((INDEX_EDGE, int(part[1:-1])))
            except ValueError as exc:
                raise MalformedPath('%r is a malformed path: %s' % (path, exc))

        else:
            # FIXME(willkg): This doesn't validate edges per the rules above. We're just going to
            # leave that out for now since it gets more processing intensive to do it.
            tokens.append((KEY_EDGE, part))
    return tokens


def tree_get(tree, path, default=NO_DEFAULT):
    """Given tree of dicts and lists, returns the value specified by the path

    Some things to know about ``tree_get()``:

    1. It doesn't alter the tree.
    2. Once it hits an edge that's missing, it returns the default or raises an error if no default
       is specified

    Examples:

    >>> tree_get({'a': 1}, 'a')
    1
    >>> tree_get({'a': 1}, 'b')
    Traceback (most recent call last)
        ...
    KeyError: 'b'
    >>> tree_get({'a': {'b': 2}}, 'a.b')
    2
    >>> tree_get({'a': {'b': 2}}, 'a.b.c', default=55)
    55
    >>> tree_get({'a': {'1': 2}}, 'a.1')
    2
    >>> tree_get({'a': [1, 2, 3]}, 'a.[1]')
    2
    >>> tree_get({'a': [{}, {'b': 'foo'}]}, 'a.[1].b')
    'foo'

    :arg dict tree: nested data structure consisting of dicts and lists and leafs of various
        types
    :arg str path: path to the value to be retrieved
    :arg varies default: default value to provide if specified, otherwise this raises an error

    :returns: value specified by the path

    :raises MalformedPath: if the path is malformed
    :raises KeyError: if no default is specified and a key in the path doesn't exist
    :raises IndexError: if no default is specified and an index in the path doesn't exist

    """
    for edge_type, edge in parse_path(path):
        if edge_type == INDEX_EDGE:
            try:
                tree = tree[edge]
            except IndexError:
                if default is NO_DEFAULT:
                    raise
                return default

        elif edge_type == KEY_EDGE:
            try:
                tree = tree[edge]
            except KeyError:
                if default is NO_DEFAULT:
                    raise
                return default

    return tree
