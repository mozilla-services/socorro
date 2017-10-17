import os
from unittest import TestCase

from crashstats.manage import utils


SAMPLE_CSV_FILE_PCI_DATABASE_COM = os.path.join(
    os.path.dirname(__file__),
    'sample-graphics.csv'
)
SAMPLE_CSV_FILE_PCI_IDS = os.path.join(
    os.path.dirname(__file__),
    'sample-pci.ids'
)


class TestUtils(TestCase):

    def test_string_hex_to_hex_string(self):
        func = utils.string_hex_to_hex_string
        assert func('919A') == '0x919a'
        assert func('0x919A') == '0x919a'

        assert func('221') == '0x0221'
        assert func('0221') == '0x0221'
        assert func('0x0221') == '0x0221'

    def test_parse_graphics_devices_iterable__pcidatabase(self):
        with open(SAMPLE_CSV_FILE_PCI_DATABASE_COM) as iterable:
            things = []
            function = utils.pcidatabase__parse_graphics_devices_iterable
            for thing in function(iterable):
                things.append(thing)

            # to be able to make these assertions you really need to
            # be familiar with the file sample-graphics.csv
            # basic test
            expected = {
                'adapter_hex': '0x002f',
                'adapter_name': '.43 ieee 1394 controller',
                'vendor_hex': '0x0033',
                'vendor_name': 'Paradyne Corp.'
            }
            assert things[0] == expected

            # same vendor as before
            expected = {
                'adapter_hex': '0x0333',
                'adapter_name': (
                    '1ACPI\\GenuineIntel_-_x86_Family_6_Model_'
                    '23\\_0 1ACPI\\GenuineIntel_-_x86_Family_6'
                    '_Model_23\\_0'
                ),
                'vendor_hex': '0x0033',
                'vendor_name': 'Paradyne Corp.'
            }
            assert things[1] == expected

            # non-utf-8 encoded charater here
            expected = {
                'adapter_hex': '0x08b2',
                'adapter_name': u'123abc logitech QuickCam\ufffd Pro 4000',
                'vendor_hex': '0x0033',
                'vendor_name': 'Paradyne Corp.'
            }
            assert things[2] == expected

            # two adapter_hexes split up
            expected = {
                'adapter_hex': '0x0200',
                'adapter_name': 'DS38xx Oregon Scientific',
                'vendor_hex': '0x0553',
                'vendor_name': 'Aiptek USA'
            }
            assert things[3] == expected
            expected = {
                'adapter_hex': '0x0201',
                'adapter_name': 'DS38xx Oregon Scientific',
                'vendor_hex': '0x0553',
                'vendor_name': 'Aiptek USA'
            }
            assert things[4] == expected

            # the adapter_hex has a _ removed
            expected = {
                'adapter_hex': '0x6128',
                'adapter_name': (
                    'USB\\VID_0C45&PID_6148&REV_0101 USB PC '
                    'Camera Plus'
                ),
                'vendor_hex': '0x0553',
                'vendor_name': 'Aiptek USA'
            }
            assert things[5] == expected
            expected = {
                'adapter_hex': '0x0221',
                'adapter_name': 'LavaPort Quad-650 PCI C/D',
                'vendor_hex': '0x0407',
                'vendor_name': 'Lava Computer MFG Inc.'
            }
            assert things[6] == expected
            assert len(things) == 7

    def test_parse_graphics_devices_iterable__pci_ids(self):
        with open(SAMPLE_CSV_FILE_PCI_IDS) as iterable:
            things = []
            function = utils.pci_ids__parse_graphics_devices_iterable
            for thing in function(iterable):
                things.append(thing)

            # to be able to make these assertions you really need to
            # be familiar with the file sample-graphics.csv
            # basic test
            expected = {
                'adapter_hex': '0x8139',
                'adapter_name': 'AT-2500TX V3 Ethernet',
                'vendor_hex': '0x0010',
                'vendor_name': 'Allied Telesis, Inc'
            }
            assert things[0] == expected
            expected = {
                'adapter_hex': '0x0001',
                'adapter_name': 'PCAN-PCI CAN-Bus controller',
                'vendor_hex': '0x001c',
                'vendor_name': 'PEAK-System Technik GmbH'
            }
            assert things[1] == expected
            assert len(things) == 6
