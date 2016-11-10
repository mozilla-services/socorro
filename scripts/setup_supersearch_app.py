# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Index supersearch fields data into elasticsearch.

This script creates a first set of data to be used by Super Search as the list
of fields it exposes to users, as well as to generate the elasticsearch
mapping for processed and raw crashes.
"""

import json
import os
from elasticsearch.helpers import bulk

from configman import Namespace
from configman.converters import class_converter

from socorro.app import generic_app


class SetupSuperSearchApp(generic_app.App):
    """Index supersearch fields data into elasticsearch. """

    app_name = 'setup-supersearch'
    app_version = '1.0'
    app_description = __doc__

    required_config = Namespace()

    required_config.add_option(
        'supersearch_fields_file',
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data',
            'supersearch_fields.json'
        ),
    )

    required_config.namespace('elasticsearch')
    required_config.elasticsearch.add_option(
        'elasticsearch_class',
        default='socorro.external.es.connection_context.ConnectionContext',
        from_string_converter=class_converter,
    )
    required_config.elasticsearch.add_option(
        'index_creator_class',
        default='socorro.external.es.index_creator.IndexCreator',
        from_string_converter=class_converter,
    )

    def main(self):
        es_index = 'socorro'

        es_context = self.config.elasticsearch.elasticsearch_class(
            config=self.config.elasticsearch
        )
        index_creator = self.config.elasticsearch.index_creator_class(
            self.config.elasticsearch
        )
        index_client = index_creator.get_index_client()

        with es_context() as conn:
            es_connection = conn

        # Create the socorro index in elasticsearch.
        index_creator.create_index(es_index, None)

        # Load the initial data set.
        data_file = open(self.config.supersearch_fields_file, 'r')
        all_fields = json.loads(data_file.read())

        # Index the data.
        actions = []
        for name, field in all_fields.iteritems():
            action = {
                '_index': es_index,
                '_type': 'supersearch_fields',
                '_id': name,
                '_source': field,
            }
            actions.append(action)

        bulk(
            client=es_connection,
            actions=actions,
        )

        # Verify data was correctly inserted.
        index_client.refresh(index=[es_index])
        total_indexed = es_connection.count(
            index=es_index,
            doc_type='supersearch_fields',
        )['count']
        total_expected = len(all_fields)

        if total_expected > total_indexed:
            indexed_fields = es_connection.search(
                index=es_index,
                doc_type='supersearch_fields',
                size=total_indexed,
            )
            indexed_fields = [x['_id'] for x in indexed_fields['hits']['hits']]

            self.config.logger.error(
                'The SuperSearch fields data was not correctly indexed, '
                '%s fields are missing from the database. Missing fields: %s',
                total_expected - total_indexed,
                list(set(all_fields.keys()) - set(indexed_fields))
            )


if __name__ == '__main__':
    generic_app.main(SetupSuperSearchApp)
