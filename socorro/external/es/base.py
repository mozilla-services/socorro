# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime


def generate_list_of_indexes(from_date, to_date, index_format):
    """Return list of indexes for crash reports processed between from_date and to_date

    The naming pattern for indexes in elasticsearch is configurable, it is
    possible to have an index per day, per week, per month...

    :arg from_date: datetime object
    :arg to_date: datetime object
    :arg index_format: the format to use for the index name

    :returns: list of strings

    """
    indexes = []
    current_date = from_date
    while current_date <= to_date:
        index_name = current_date.strftime(index_format)

        # Make sure no index is twice in the list
        # (for weekly or monthly indexes for example)
        if index_name not in indexes:
            indexes.append(index_name)
        current_date += datetime.timedelta(days=1)

    return indexes
