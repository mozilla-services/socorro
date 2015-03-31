import os
from unittest import TestCase

from nose.tools import eq_

from crashstats.manage.utils import (
    parse_graphics_devices_iterable,
    string_hex_to_hex_string
)


SAMPLE_CSV_FILE = os.path.join(
    os.path.dirname(__file__),
    'sample-graphics.csv'
)


class TestUtils(TestCase):

    def test_string_hex_to_hex_string(self):
        eq_(string_hex_to_hex_string('919A'), '0x919a')
        eq_(string_hex_to_hex_string('0x919A'), '0x919a')

        eq_(string_hex_to_hex_string('221'), '0x0221')
        eq_(string_hex_to_hex_string('0221'), '0x0221')
        eq_(string_hex_to_hex_string('0x0221'), '0x0221')

    def test_parse_graphics_devices_iterable(self):
        iterable = open(SAMPLE_CSV_FILE)
        try:
            things = []
            for thing in parse_graphics_devices_iterable(iterable):
                things.append(thing)

            # to be able to make these assertions you really need to
            # be familiar with the file sample-graphics.csv
            # basic test
            eq_(
                things[0],
                {
                    'adapter_hex': '0x002f',
                    'adapter_name': '.43 ieee 1394 controller',
                    'vendor_hex': '0x0033',
                    'vendor_name': 'Paradyne Corp.'
                }
            )
            # same vendor as before
            eq_(
                things[1],
                {
                    'adapter_hex': '0x0333',
                    'adapter_name': '1ACPI\\GenuineIntel_-_x86_Family_6_Model_'
                                    '23\\_0 1ACPI\\GenuineIntel_-_x86_Family_6'
                                    '_Model_23\\_0',
                    'vendor_hex': '0x0033',
                    'vendor_name': 'Paradyne Corp.'
                }
            )
            # non-utf-8 encoded charater here
            eq_(
                things[2],
                {
                    'adapter_hex': '0x08b2',
                    'adapter_name': u'123abc logitech QuickCam\ufffd Pro 4000',
                    'vendor_hex': '0x0033',
                    'vendor_name': 'Paradyne Corp.'
                }
            )
            # two adapter_hexes split up
            eq_(
                things[3],
                {
                    'adapter_hex': '0x0200',
                    'adapter_name': 'DS38xx Oregon Scientific',
                    'vendor_hex': '0x0553',
                    'vendor_name': 'Aiptek USA'
                }
            )
            eq_(
                things[4],
                {
                    'adapter_hex': '0x0201',
                    'adapter_name': 'DS38xx Oregon Scientific',
                    'vendor_hex': '0x0553',
                    'vendor_name': 'Aiptek USA'
                }
            )
            # the adapter_hex has a _ removed
            eq_(
                things[5],
                {
                    'adapter_hex': '0x6128',
                    'adapter_name': 'USB\\VID_0C45&PID_6148&REV_0101 USB PC '
                                    'Camera Plus',
                    'vendor_hex': '0x0553',
                    'vendor_name': 'Aiptek USA'
                }
            )
            eq_(
                things[6],
                {
                    'adapter_hex': '0x0221',
                    'adapter_name': 'LavaPort Quad-650 PCI C/D',
                    'vendor_hex': '0x0407',
                    'vendor_name': 'Lava Computer MFG Inc.'
                }
            )
            eq_(len(things), 7)

        finally:
            iterable.close()
