# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import mock

from socorro.lib.util import DotDict
from socorro.collector.throttler import (
  LegacyThrottler,
  ACCEPT,
  DEFER,
  DISCARD,
  IGNORE
)

def testLegacyThrottler():

    # phase 1 tests

    config = DotDict()
    config.throttle_conditions = [ ('alpha', re.compile('ALPHA'), 100),
                                   ('beta',  'BETA', 100),
                                   ('gamma', lambda x: x == 'GAMMA', 100),
                                   ('delta', True, 100),
                                   (None, True, 0)
                                  ]
    config.minimal_version_for_understanding_refusal = {
      'product1': '3.5',
      'product2': '4.0'
    }
    config.never_discard = False
    config.logger = mock.Mock()
    thr = LegacyThrottler(config)
    expected = 5
    actual = len(thr.processed_throttle_conditions)
    assert expected == actual, \
      "expected thr.preprocessThrottleConditions to have length %d, but got " \
      "%d instead" % (expected, actual)

    raw_crash = DotDict({ 'ProductName':'product1',
                          'Version':'3.0',
                          'alpha':'ALPHA',
                          })
    expected = False
    actual = thr.understands_refusal(raw_crash)
    assert expected == actual, \
      "understand refusal expected %d, but got %d instead" % (expected, actual)

    raw_crash = DotDict({ 'ProductName':'product1',
                          'Version':'3.6',
                          'alpha':'ALPHA',
                          })
    expected = True
    actual = thr.understands_refusal(raw_crash)
    assert expected == actual, \
      "understand refusal expected %d, but got %d instead" % (expected, actual)

    expected = (ACCEPT, 100)
    actual = thr.throttle(raw_crash)
    assert expected == actual, \
      "regexp throttle expected %d, but got %d instead" % (expected, actual)

    raw_crash = DotDict({ 'ProductName':'product1',
                          'Version':'3.4',
                          'alpha':'not correct',
                          })
    expected = (DEFER, 0)
    actual = thr.throttle(raw_crash)
    assert expected == actual, \
      "regexp throttle expected %d, but got %d instead" % (expected, actual)

    raw_crash = DotDict({ 'ProductName':'product1',
                          'Version':'3.6',
                          'alpha':'not correct',
                          })
    expected = (DISCARD, 0)
    actual = thr.throttle(raw_crash)
    assert expected == actual, \
      "regexp throttle expected %d, but got %d instead" % (expected, actual)

    raw_crash = DotDict({ 'ProductName':'product1',
                          'Version':'3.6',
                          'beta':'BETA',
                          })
    expected = (ACCEPT, 100)
    actual = thr.throttle(raw_crash)
    assert expected == actual, \
      "string equality throttle expected %d, but got %d instead" % \
      (expected, actual)

    raw_crash = DotDict({ 'ProductName':'product1',
                          'Version':'3.6',
                          'beta':'not BETA',
                          })
    expected = (DISCARD, 0)
    actual = thr.throttle(raw_crash)
    assert expected == actual, \
      "string equality throttle expected %d, but got %d instead" % \
      (expected, actual)

    raw_crash = DotDict({ 'ProductName':'product1',
                          'Version':'3.6',
                          'gamma':'GAMMA',
                          })
    expected = (ACCEPT, 100)
    actual = thr.throttle(raw_crash)
    assert expected == actual, \
      "string equality throttle expected %d, but got %d instead" % \
      (expected, actual)

    raw_crash = DotDict({ 'ProductName':'product1',
                          'Version':'3.6',
                          'gamma':'not GAMMA',
                          })
    expected = (DISCARD, 0)
    actual = thr.throttle(raw_crash)
    assert expected == actual, \
      "string equality throttle expected %d, but got %d instead" % \
      (expected, actual)

    raw_crash = DotDict({ 'ProductName':'product1',
                          'Version':'3.6',
                          'delta':"value doesn't matter",
                          })
    expected = (ACCEPT, 100)
    actual = thr.throttle(raw_crash)
    assert expected == actual, \
      "string equality throttle expected %d, but got %d instead" % \
      (expected, actual)

    # phase 2 tests

    config = DotDict()
    config.throttle_conditions = [
      ('*', lambda x: 'alpha' in x, None),
      ('*', lambda x: x['beta'] == 'BETA', 100),
    ]
    config.minimal_version_for_understanding_refusal = {
      'product1': '3.5',
      'product2': '4.0'
    }
    config.never_discard = True
    config.logger = mock.Mock()
    thr = LegacyThrottler(config)
    expected = 2
    actual = len(thr.processed_throttle_conditions)
    assert expected == actual, \
      "expected thr.preprocessThrottleConditions to have length %d, but got " \
      "%d instead" % (expected, actual)

    raw_crash = DotDict({ 'ProductName':'product1',
                          'Version':'3.6',
                          'beta': 'ugh',
                          'alpha':"value doesn't matter",
                          })
    expected = (IGNORE, None)
    actual = thr.throttle(raw_crash)
    assert expected == actual, \
      "IGNORE expected %d, but got %d instead" % \
      (expected, actual)

    raw_crash = DotDict({ 'ProductName':'product1',
                          'Version':'3.6',
                          'beta': 'ugh',
                          'delta':"value doesn't matter",
                          })
    expected = (DEFER, 0)
    actual = thr.throttle(raw_crash)
    assert expected == actual, \
      "DEFER expected %d, but got %d instead" % \
      (expected, actual)

    raw_crash = DotDict({ 'ProductName':'product1',
                          'Version':'3.6',
                          'beta': 'BETA',
                          'alpha':"value doesn't matter",
                          })
    expected = (IGNORE, None)
    actual = thr.throttle(raw_crash)
    assert expected == actual, \
      "IGNORE expected %d, but got %d instead" % \
      (expected, actual)
    raw_crash = DotDict({ 'ProductName':'product1',
                          'Version':'3.6',
                          'beta': 'BETA',
                          'delta':"value doesn't matter",
                          })
    expected = (ACCEPT, 100)
    actual = thr.throttle(raw_crash)
    assert expected == actual, \
      "ACCEPT expected %d, but got %d instead" % \
      (expected, actual)

