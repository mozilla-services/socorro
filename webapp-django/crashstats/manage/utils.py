# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import six

from django.utils.encoding import smart_text


def string_hex_to_hex_string(snippet):
    """The PCIDatabase.com uses shortened hex strings (e.g. '919A')
    whereas in Socorro we use the full represenation, but still as a
    string (e.g. '0x919a').
    Also, note that when converting the snippet to a 16 base int, we
    can potentially lose the leading zeros, but we want to make sure
    we always return a 4 character string preceeded by 0x.
    This function tries to make that conversion.
    """
    assert isinstance(snippet, six.string_types)
    return '0x' + format(int(snippet, 16), '04x')


def pci_ids__parse_graphics_devices_iterable(iterable):
    """
    This function is for parsing the CSVish files from https://pci-ids.ucw.cz/

    yield dicts that contain the following keys:
        * vendor_hex
        * vendor_name
        * adapter_hex
        * adapter_name

    Rows that start with a `#` are considered comments.
    The structure is expected to be like this:

        XXX \t Vendor Name 1
        \t AAA \t Adapter Name 1
        \t BBB \t Adapter Name 2
        YYY \t Vendor Name 2
        \t CCC \t Adapter Name N

    """
    for line in iterable:
        line = smart_text(line)
        if line.startswith('#'):
            if 'List of known device classes' in line:
                # There's a section at the bottom of the files which
                # we don't need to parse.
                break
            continue
        if not line.strip():
            continue
        if not line.startswith('\t'):
            try:
                vendor_hex, vendor_name = line.strip().split(None, 1)
            except ValueError:
                continue
        else:
            if (
                line.strip().startswith(vendor_hex) and
                len(line.strip().split()) > 2
            ):
                _, adapter_hex, adapter_name = line.strip().split(None, 2)
            else:
                adapter_hex, adapter_name = line.strip().split(None, 1)
            try:
                vendor_hex = string_hex_to_hex_string(vendor_hex)
                adapter_hex = string_hex_to_hex_string(adapter_hex)
                yield {
                    'vendor_hex': vendor_hex,
                    'vendor_name': vendor_name,
                    'adapter_hex': adapter_hex,
                    'adapter_name': adapter_name
                }
            except ValueError:
                continue
