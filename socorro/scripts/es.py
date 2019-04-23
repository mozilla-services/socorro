# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Elasticsearch manipulation script for deleting and creating Elasticsearch
indices.
"""

import argparse
import datetime
import os

from configman import configuration, Namespace

from socorro.external.es.base import generate_list_of_indexes
from socorro.external.es.connection_context import ConnectionContext
from socorro.scripts import WrappedTextHelpFormatter


DESCRIPTION = 'Create and delete Elasticsearch indices'

EPILOG = 'Requires Elasticsearch configuration to be set in environment.'


def get_conn():
    ns = Namespace()
    ns.add_option('elasticsearch_class', default=ConnectionContext)

    config = configuration(
        definition_source=ns,
        values_source_list=[{
            'elasticsearch_urls': os.environ.get('ELASTICSEARCH_URLS', 'http://localhost:9200')
        }]
    )

    return ConnectionContext(config)


def main(argv=None):
    parser = argparse.ArgumentParser(
        formatter_class=WrappedTextHelpFormatter,
        description=DESCRIPTION.strip(),
        epilog=EPILOG.strip()
    )
    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True
    create_parser = subparsers.add_parser('create', help='create indices')
    create_parser.add_argument(
        '--future', type=int, default=2,
        help='Number of weeks in the future to create.'
    )
    create_parser.add_argument(
        '--past', type=int, default=2,
        help='Number of weeks in the future to create.'
    )

    args = parser.parse_args()
    conn = get_conn()

    if args.cmd == 'create':
        # Create recent indices
        index_name_template = conn.get_index_template()

        # Figure out dates
        today = datetime.date.today()
        from_date = today - datetime.timedelta(weeks=args.past)
        to_date = today + datetime.timedelta(weeks=args.future)

        # Create indiices
        index_names = generate_list_of_indexes(from_date, to_date, index_name_template)
        for index_name in index_names:
            was_created = conn.create_index(index_name)
            if was_created:
                print('Index %s was created.' % index_name)
            else:
                print('Index %s already existed.' % index_name)
