# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from socorro.processor.externalProcessor import ProcessorWithExternalBreakpad
from socorro.lib.util import DotDict


class Abused_ProcessorWithExternalBreakpad(ProcessorWithExternalBreakpad):

    def __init__(self, config):
        self.config = config


class TestProcessorWithExternalBreakpad(unittest.TestCase):

    def test_getVersionIfFlashModule(self):
        config = DotDict()
        config.knownFlashDebugIdentifiers = {'yyy': '9.0'}
        proc = Abused_ProcessorWithExternalBreakpad(config)

        # junk moduleData
        moduleData = []
        version = proc.getVersionIfFlashModule(moduleData)
        self.assertTrue(not version)

        moduleData = ['xxx', 'doesntmatter', '0.0', 'xxx', 'xxx']
        version = proc.getVersionIfFlashModule(moduleData)
        self.assertEqual(version, None)

        moduleData[1] = 'gobblygook'
        version = proc.getVersionIfFlashModule(moduleData)
        self.assertEqual(version, None)

        moduleData[1] = 'Flash Player-10.4'
        version = proc.getVersionIfFlashModule(moduleData)
        self.assertEqual(version, '0.0')

        moduleData[1] = 'Flash Player-10.4'
        moduleData[2] = ''
        version = proc.getVersionIfFlashModule(moduleData)
        self.assertEqual(version, '10.4')

        moduleData[1] = 'libflashplayer2.1_3.so'
        moduleData[2] = '0.0'
        version = proc.getVersionIfFlashModule(moduleData)
        self.assertEqual(version, '0.0')  # matched but use the defaul

        moduleData[1] = 'libflashplayer2.1_3.so'
        moduleData[2] = ''
        version = proc.getVersionIfFlashModule(moduleData)
        self.assertEqual(version, '2.1_3')

        moduleData[1] = 'NPSWF32_11_2_202_228.dll'
        moduleData[2] = '11.2.444'
        version = proc.getVersionIfFlashModule(moduleData)
        self.assertEqual(version, '11.2.444')

        moduleData[1] = 'NPSWF32_11_2_202_228.dll'
        moduleData[2] = ''
        version = proc.getVersionIfFlashModule(moduleData)
        self.assertEqual(version, '11.2.202.228')

        # it's case sensitive
        moduleData[1] = 'NPSWF32_11_2_202_228.DLL'
        version = proc.getVersionIfFlashModule(moduleData)
        self.assertEqual(version, None)

        moduleData[1] = 'NPSWF32.dll'  # filename
        moduleData[2] = ''  # version
        moduleData[4] = 'yyy'  # debugId (see above)
        version = proc.getVersionIfFlashModule(moduleData)
        self.assertEqual(version, '9.0')
