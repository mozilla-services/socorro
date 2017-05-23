# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import socorro.lib.ver_tools as vtl

phs = vtl._padding_high_string
pl  = vtl._padding_list

tests = [('3',            [3, phs, 0, phs] + pl * 3, '3'),
         ('3.',           [3, phs, 0, phs] + pl * 3, '3'),
         ('3.0',          [3, phs, 0, phs] + pl * 3, '3'),
         ('3.0.0',        [3, phs, 0, phs] + pl * 3, '3'),
         ('3.5',          [3, phs, 0, phs,
                           5, phs, 0, phs] + pl * 2, '3.5'),
         ('3.5pre',       [3, phs, 0, phs,
                           5, 'pre', 0, phs] + pl * 2, '3.5pre'),
         ('3.5b3',        [3, phs, 0, phs,
                           5, 'b', 3, phs] + pl * 2, '3.5b3'),

         ('3.6.4plugin3', [3, phs, 0, phs,
                           6, phs, 0, phs,
                           4, 'plugin', 3, phs] + pl, '3.6.4plugin3'),
        ]

def testNormalize():
    for ver, expected, ver2 in tests:
        got = vtl.normalize(ver)
        assert got == expected, "expected %s, but got %s" % (expected, got)

def testDenomalize():
    for ver, norm, expected in tests:
        got = vtl.denormalize(norm)
        assert got == expected, "expected %s, but got %s" % (expected, got)

def testCompare():
    got = vtl.compare('3', '3.1')
    assert got == -1, "expected %s, but got %s" % (-1, got)
    got = vtl.compare('3', '3.0')
    assert got == 0, "expected %s, but got %s" % (0, got)
    got = vtl.compare('3', '3.0pre')
    assert got == 1, "expected %s, but got %s" % (1, got)
    got = vtl.compare('3.5b2', '3.5b1')
    assert got == 1, "expected %s, but got %s" % (1, got)
    got = vtl.compare('3.5', '3.5b1')
    assert got == 1, "expected %s, but got %s" % (1, got)
    got = vtl.compare('3.5.1', '3.5.1b3')
    assert got == 1, "expected %s, but got %s" % (1, got)
