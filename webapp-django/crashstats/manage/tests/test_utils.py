import os
from unittest import TestCase

from crashstats.manage import utils


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
