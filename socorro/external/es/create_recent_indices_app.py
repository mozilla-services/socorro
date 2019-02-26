#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from datetime import date, timedelta
import sys

from configman import Namespace, class_converter

from socorro.app.socorro_app import App
from socorro.external.es.base import generate_list_of_indexes


class CreateRecentESIndicesApp(App):
    """Creates week-based crash indices in Elasticsearch previous 2 weeks and upcoming weeks"""
    app_name = 'create_recent_es_indices'
    app_version = '1.0'
    app_description = __doc__

    required_config = Namespace()
    required_config.add_option(
        'elasticsearch_class',
        doc='an elasticsearch connection context to create indices',
        default='socorro.external.es.connection_context.ConnectionContext',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'weeks_to_create_future',
        default=2,
        reference_value_from='resource.elasticsearch',
    )
    required_config.add_option(
        'weeks_to_create_past',
        default=2,
        reference_value_from='resource.elasticsearch',
    )

    def main(self):
        context = self.config.elasticsearch_class(self.config)
        index_name_template = context.get_index_template()

        # Figure out dates
        today = date.today()
        from_date = today - timedelta(weeks=self.config.weeks_to_create_past)
        to_date = today + timedelta(weeks=self.config.weeks_to_create_future)

        # Create indexes
        index_names = generate_list_of_indexes(from_date, to_date, index_name_template)
        for index_name in index_names:
            context.create_socorro_index(index_name, log_result=True)


if __name__ == '__main__':
    sys.exit(CreateRecentESIndicesApp.run())
