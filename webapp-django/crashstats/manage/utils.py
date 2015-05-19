def string_hex_to_hex_string(snippet):
    """The PCIDatabase.com uses shortened hex strings (e.g. '919A')
    whereas in Socorro we use the full represenation, but still as a
    string (e.g. '0x919a').
    Also, note that when converting the snippet to a 16 base int, we
    can potentially lose the leading zeros, but we want to make sure
    we always return a 4 character string preceeded by 0x.
    This function tries to make that conversion.
    """
    assert isinstance(snippet, basestring)
    return '0x' + format(int(snippet, 16), '04x')


def pcidatabase__parse_graphics_devices_iterable(iterable, delimiter='\t'):
    """
    This function is for parsing CSVish files from PCIDatabase.com

    yield dicts that contain the following keys:
        * vendor_hex
        * vendor_name
        * adapter_hex
        * adapter_name

    Rows that start with a `;` are considered comments.
    The structure is expected to be like this:

        XXX \t Vendor Name 1
        \t AAA \t Adapter Name 1
        \t BBB \t Adapter Name 2
        YYY \t Vendor Name 2
        \t CCC \t Adapter Name N

    """
    for line in iterable:
        if line.startswith(';'):
            continue
        try:
            line = unicode(line, 'utf-8')
        except UnicodeDecodeError:
            try:
                # the PCIDatabase.com's CSV file uses this
                line = unicode(line, 'cp1252')
            except UnicodeDecodeError:
                continue
        split = [x.strip() for x in line.rstrip().split(delimiter)]
        if len(split) == 2 and split[0]:
            vendor_hex, vendor_name = split
            vendor_hex = string_hex_to_hex_string(vendor_hex)
        elif len(split) == 3 and not split[0] and split[1] and split[2]:
            if split[2] in ('n/a', 'n/a n/a'):
                # some adapter names appear to be entered in this
                # format instead of just being left empty
                continue
            adapter_hexes, adapter_name = split[1:]
            adapter_hexes = [
                x.strip() for x in adapter_hexes.split(',') if x.strip()
            ]
            for adapter_hex in adapter_hexes:
                if adapter_hex.endswith('_'):
                    adapter_hex = adapter_hex[:-1]
                try:
                    adapter_hex = string_hex_to_hex_string(adapter_hex)
                    yield {
                        'vendor_hex': vendor_hex,
                        'vendor_name': vendor_name,
                        'adapter_hex': adapter_hex,
                        'adapter_name': adapter_name
                    }
                except ValueError:
                    # possibly a mistakenly badly formatted piece of
                    # hex string
                    pass


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
