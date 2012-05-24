import re
import mock

from socorro.lib.util import DotDict
from socorro.collector.throttler import LegacyThrottler

def testLegacyThrottler():
  config = DotDict()
  config.throttleConditions = [ ('alpha', re.compile('ALPHA'), 100),
                                ('beta',  'BETA', 100),
                                ('gamma', lambda x: x == 'GAMMA', 100),
                                ('delta', True, 100),
                                (None, True, 0)
                              ]
  config.minimalVersionForUnderstandingRefusal = { 'product1': '3.5', 'product2': '4.0' }
  config.neverDiscard = False
  config.logger = mock.Mock()
  thr = LegacyThrottler(config)
  expected = 5
  actual = len(thr.processed_throttle_conditions)
  assert expected == actual, "expected thr.preprocessThrottleConditions to have length %d, but got %d instead" % (expected, actual)

  raw_crash = DotDict({ 'ProductName':'product1',
                         'Version':'3.0',
                         'alpha':'ALPHA',
                       })
  expected = False
  actual = thr.understands_refusal(raw_crash)
  assert expected == actual, "understand refusal expected %d, but got %d instead" % (expected, actual)

  raw_crash = DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'alpha':'ALPHA',
                       })
  expected = True
  actual = thr.understands_refusal(raw_crash)
  assert expected == actual, "understand refusal expected %d, but got %d instead" % (expected, actual)

  expected = LegacyThrottler.ACCEPT
  actual = thr.throttle(raw_crash)
  assert expected == actual, "regexp throttle expected %d, but got %d instead" % (expected, actual)

  raw_crash = DotDict({ 'ProductName':'product1',
                         'Version':'3.4',
                         'alpha':'not correct',
                       })
  expected = LegacyThrottler.DEFER
  actual = thr.throttle(raw_crash)
  assert expected == actual, "regexp throttle expected %d, but got %d instead" % (expected, actual)

  raw_crash = DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'alpha':'not correct',
                       })
  expected = LegacyThrottler.DISCARD
  actual = thr.throttle(raw_crash)
  assert expected == actual, "regexp throttle expected %d, but got %d instead" % (expected, actual)

  raw_crash = DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'beta':'BETA',
                       })
  expected = LegacyThrottler.ACCEPT
  actual = thr.throttle(raw_crash)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)

  raw_crash = DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'beta':'not BETA',
                       })
  expected = LegacyThrottler.DISCARD
  actual = thr.throttle(raw_crash)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)

  raw_crash = DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'gamma':'GAMMA',
                       })
  expected = LegacyThrottler.ACCEPT
  actual = thr.throttle(raw_crash)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)

  raw_crash = DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'gamma':'not GAMMA',
                       })
  expected = LegacyThrottler.DISCARD
  actual = thr.throttle(raw_crash)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)

  raw_crash = DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'delta':"value doesn't matter",
                       })
  expected = LegacyThrottler.ACCEPT
  actual = thr.throttle(raw_crash)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)

