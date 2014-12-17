# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime


class ElasticsearchBase(object):

    def __init__(self, *args, **kwargs):
        self.config = kwargs.get('config')
        self.es_context = self.config.elasticsearch.elasticsearch_class(
            self.config.elasticsearch
        )

    def get_connection(self):
        with self.es_context() as conn:
            return conn

    def generate_list_of_indexes(self, from_date, to_date, es_index=None):
        """Return the list of indexes to query to access all the crash reports
        that were processed between from_date and to_date.

        The naming pattern for indexes in elasticsearch is configurable, it is
        possible to have an index per day, per week, per month...

        Parameters:
        * from_date datetime object
        * to_date datetime object
        """
        if es_index is None:
            es_index = self.config.elasticsearch.elasticsearch_index

        indexes = []
        current_date = from_date
        while current_date <= to_date:
            index = current_date.strftime(es_index)

            # Make sure no index is twice in the list
            # (for weekly or monthly indexes for example)
            if index not in indexes:
                indexes.append(index)
            current_date += datetime.timedelta(days=1)

        return indexes
