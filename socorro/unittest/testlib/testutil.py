# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import socorro.unittest.testlib.util as tutil
import os

def setup_module():
  tutil.nosePrintModule(__file__)

def testGetModuleFromFile():
  os.path.sep = '/'
  testData = [
    {'kwargs':{'filename':None},
     'expect': '\n==== Unknown Module ====\n========================' },
    {'kwargs':{'filename':None, 'depth':4},
     'expect':'\n==== Unknown Module ====\n========================' },
    {'kwargs':{'filename':None, 'decorate':False},
     'expect': 'Unknown Module' },
    {'kwargs':{'filename':None, 'decorate':'Nothing Useful'},
     'expect': 'Nothing Useful' },

    {'kwargs':{'filename':'toot'},
     'expect': '\n==== toot ====\n=============='},
    {'kwargs':{'filename':'toot', 'depth':4},
     'expect': '\n==== toot ====\n=============='},
    {'kwargs':{'filename':'toot', 'decorate':False},
     'expect': 'toot' },
    {'kwargs':{'filename':'toot', 'decorate':'Nothing Useful'},
     'expect': 'Nothing Useful' },

    {'kwargs':{'filename':'/toot'},
     'expect': '\n==== toot ====\n=============='},
    {'kwargs':{'filename':'/toot', 'depth':4},
     'expect': '\n==== toot ====\n=============='},
    {'kwargs':{'filename':'/toot', 'decorate':False},
     'expect': 'toot' },
    {'kwargs':{'filename':'/toot', 'decorate':'Nothing Useful'},
     'expect': 'Nothing Useful' },

    {'kwargs':{'filename':'toot/suite'},
     'expect': '\n==== toot.suite ====\n===================='},
    {'kwargs':{'filename':'toot/suite', 'depth':4},
     'expect': '\n==== toot.suite ====\n===================='},
    {'kwargs':{'filename':'toot/suite', 'depth':1},
     'expect': '\n==== suite ====\n==============='},
    {'kwargs':{'filename':'toot/suite', 'decorate':False},
     'expect': 'toot.suite' },
    {'kwargs':{'filename':'toot', 'decorate':'Nothing Useful'},
     'expect': 'Nothing Useful' },

    {'kwargs':{'filename':'toot/suite/pronto'},
     'expect': '\n==== toot.suite.pronto ====\n==========================='},
    {'kwargs':{'filename':'toot/suite/pronto', 'depth':4},
     'expect': '\n==== toot.suite.pronto ====\n==========================='},
    {'kwargs':{'filename':'toot/suite/pronto', 'depth':2},
     'expect': '\n==== suite.pronto ====\n======================'},
    {'kwargs':{'filename':'toot/suite/pronto', 'decorate':False},
     'expect': 'toot.suite.pronto' },
    {'kwargs':{'filename':'toot/suite/pronto', 'decorate':'Nothing Useful'},
     'expect': 'Nothing Useful' },

    {'kwargs':{'filename':'toot/suite/pronto/now/really/baby'},
     'expect': '\n==== pronto.now.really.baby ====\n================================' },
    {'kwargs':{'filename':'toot/suite/pronto/now/really/baby', 'depth':4},
     'expect': '\n==== pronto.now.really.baby ====\n================================' },
    {'kwargs':{'filename':'toot/suite/pronto/now/really/baby', 'decorate':False},
     'expect': 'pronto.now.really.baby' },
    {'kwargs':{'filename':'toot/suite/pronto/now/really/baby', 'decorate':'Nothing Useful'},
     'expect': 'Nothing Useful' },
    ]
  for td in testData:
    got = tutil.getModuleFromFile(**td['kwargs'])
    assert td['expect'] == got, 'expected [%s] but got [%s]'%(td['expect'],got)

# def testStopImmediately(): Too silly to test this one

# def testRunInOtherProcess(): Too hard to test this one
