# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
OOID is "Our opaque ID"
"""

import datetime
import re
import uuid

from socorro.lib.libdatetime import utc_now, UTC


DEFAULT_DEPTH = 2


def create_new_ooid(timestamp=None, depth=DEFAULT_DEPTH):
    """Create a new Ooid for a given time and depth

    :arg datetime timestamp: the timestamp to encode; defaults to UTC now
    :arg int depth: the depth to encode; defaults to 2

    """
    if not timestamp:
        timestamp = utc_now().date()
    assert depth <= 4 and depth >= 1
    new_uuid = str(uuid.uuid4())
    return "%s%d%02d%02d%02d" % (
        new_uuid[:-7],
        depth,
        timestamp.year % 100,
        timestamp.month,
        timestamp.day,
    )


def depth_from_ooid(ooid):
    """Extract the encoded expected storage depth from an ooid.

    :arg str ooid: The ooid from which to extract the info

    :returns: expected depth if the ooid is in expected format else None

    """
    try:
        return int(ooid[-7])
    except (ValueError, IndexError):
        return None


def date_from_ooid(ooid):
    """Extract the encoded date from an ooid

    :arg str ooid: the ooid from which to extract the info

    :returns: date as a datetime or None

    """
    try:
        return datetime.datetime(
            2000 + int(ooid[-6:-4]), int(ooid[-4:-2]), int(ooid[-2:]), tzinfo=UTC
        )
    except (ValueError, TypeError, IndexError):
        return None


CRASH_ID_RE = re.compile(
    r"""
    ^
    [a-f0-9]{8}-
    [a-f0-9]{4}-
    [a-f0-9]{4}-
    [a-f0-9]{4}-
    [a-f0-9]{6}
    [0-9]{6}      # date in YYMMDD
    $
""",
    re.VERBOSE,
)


def is_crash_id_valid(crash_id):
    """Returns whether this is a valid crash id

    :arg str crash_id: the crash id in question

    :returns: True if it's valid, False if not

    """
    return bool(CRASH_ID_RE.match(crash_id))
