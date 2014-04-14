import os
from unittest import TestCase

from nose.tools import eq_

from crashstats.manage.utils import parse_graphics_devices_iterable


SAMPLE_CSV_FILE = os.path.join(
    os.path.dirname(__file__),
    'sample-graphics.csv'
)


class TestUtils(TestCase):

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
                    'adapter_hex': '0x2f',
                    'adapter_name': '.43 ieee 1394 controller',
                    'vendor_hex': '0x33',
                    'vendor_name': 'Paradyne Corp.'
                }
            )
            # same vendor as before
            eq_(
                things[1],
                {
                    'adapter_hex': '0x333',
                    'adapter_name': '1ACPI\\GenuineIntel_-_x86_Family_6_Model_'
                                    '23\\_0 1ACPI\\GenuineIntel_-_x86_Family_6'
                                    '_Model_23\\_0',
                    'vendor_hex': '0x33',
                    'vendor_name': 'Paradyne Corp.'
                }
            )
            # non-utf-8 encoded charater here
            eq_(
                things[2],
                {
                    'adapter_hex': '0x8b2',
                    'adapter_name': u'123abc logitech QuickCam\xae Pro 4000',
                    'vendor_hex': '0x33',
                    'vendor_name': 'Paradyne Corp.'
                }
            )
            # two adapter_hexes split up
            eq_(
                things[3],
                {
                    'adapter_hex': '0x200',
                    'adapter_name': 'DS38xx Oregon Scientific',
                    'vendor_hex': '0x553',
                    'vendor_name': 'Aiptek USA'
                }
            )
            eq_(
                things[4],
                {
                    'adapter_hex': '0x201',
                    'adapter_name': 'DS38xx Oregon Scientific',
                    'vendor_hex': '0x553',
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
                    'vendor_hex': '0x553',
                    'vendor_name': 'Aiptek USA'
                }
            )
            eq_(len(things), 6)

        finally:
            iterable.close()
