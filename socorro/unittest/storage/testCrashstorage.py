# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock
import os
import sys
import re
import json

import socorro.storage.crashstorage as cstore
import socorro.unittest.testlib.expectations as exp
import socorro.lib.util as util

import socorro.unittest.testlib.loggerForTest as loggerForTest

def testLegacyThrottler():
  config = util.DotDict()
  config.throttleConditions = [ ('alpha', re.compile('ALPHA'), 100),
                                ('beta',  'BETA', 100),
                                ('gamma', lambda x: x == 'GAMMA', 100),
                                ('delta', True, 100),
                                (None, True, 0)
                              ]
  config.minimalVersionForUnderstandingRefusal = { 'product1': '3.5', 'product2': '4.0' }
  config.neverDiscard = False
  config.logger = util.SilentFakeLogger()
  thr = cstore.LegacyThrottler(config)
  expected = 5
  actual = len(thr.processedThrottleConditions)
  assert expected == actual, "expected thr.preprocessThrottleConditions to have length %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.0',
                         'alpha':'ALPHA',
                       })
  expected = False
  actual = thr.understandsRefusal(json1)
  assert expected == actual, "understand refusal expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'alpha':'ALPHA',
                       })
  expected = True
  actual = thr.understandsRefusal(json1)
  assert expected == actual, "understand refusal expected %d, but got %d instead" % (expected, actual)

  expected = cstore.LegacyThrottler.ACCEPT
  actual = thr.throttle(json1)
  assert expected == actual, "regexp throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.4',
                         'alpha':'not correct',
                       })
  expected = cstore.LegacyThrottler.DEFER
  actual = thr.throttle(json1)
  assert expected == actual, "regexp throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'alpha':'not correct',
                       })
  expected = cstore.LegacyThrottler.DISCARD
  actual = thr.throttle(json1)
  assert expected == actual, "regexp throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'beta':'BETA',
                       })
  expected = cstore.LegacyThrottler.ACCEPT
  actual = thr.throttle(json1)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'beta':'not BETA',
                       })
  expected = cstore.LegacyThrottler.DISCARD
  actual = thr.throttle(json1)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'gamma':'GAMMA',
                       })
  expected = cstore.LegacyThrottler.ACCEPT
  actual = thr.throttle(json1)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'gamma':'not GAMMA',
                       })
  expected = cstore.LegacyThrottler.DISCARD
  actual = thr.throttle(json1)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'delta':"value doesn't matter",
                       })
  expected = cstore.LegacyThrottler.ACCEPT
  actual = thr.throttle(json1)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)
    # phase 2 tests

  config = util.DotDict()
  config.throttleConditions = [
    ('*', lambda x: 'alpha' in x, None),
    ('*', lambda x: x['beta'] == 'BETA', 100),
  ]
  config.minimalVersionForUnderstandingRefusal = {
    'product1': '3.5',
    'product2': '4.0'
  }
  config.neverDiscard = True
  config.logger = mock.Mock()
  thr = cstore.LegacyThrottler(config)
  expected = 2
  actual = len(thr.processedThrottleConditions)
  assert expected == actual, \
    "expected thr.preprocessThrottleConditions to have length %d, but got " \
    "%d instead" % (expected, actual)

  raw_crash = util.DotDict({ 'ProductName':'product1',
                             'Version':'3.6',
                             'beta': 'ugh',
                             'alpha':"value doesn't matter",
                          })
  expected = cstore.LegacyThrottler.IGNORE
  actual = thr.throttle(raw_crash)
  assert expected == actual, \
    "IGNORE expected %d, but got %d instead" % \
    (expected, actual)

  raw_crash = util.DotDict({ 'ProductName':'product1',
                             'Version':'3.6',
                             'beta': 'ugh',
                             'delta':"value doesn't matter",
                          })
  expected = cstore.LegacyThrottler.DEFER
  actual = thr.throttle(raw_crash)
  assert expected == actual, \
    "DEFER expected %d, but got %d instead" % \
    (expected, actual)

  raw_crash = util.DotDict({ 'ProductName':'product1',
                             'Version':'3.6',
                             'beta': 'BETA',
                             'alpha':"value doesn't matter",
                          })
  expected = cstore.LegacyThrottler.IGNORE
  actual = thr.throttle(raw_crash)
  assert expected == actual, \
    "IGNORE expected %d, but got %d instead" % \
    (expected, actual)
  raw_crash = util.DotDict({ 'ProductName':'product1',
                             'Version':'3.6',
                             'beta': 'BETA',
                             'delta':"value doesn't matter",
                          })
  expected = cstore.LegacyThrottler.ACCEPT
  actual = thr.throttle(raw_crash)
  assert expected == actual, \
    "ACCEPT expected %d, but got %d instead" % \
    (expected, actual)
