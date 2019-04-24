# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Elasticsearch manipulation script for deleting and creating Elasticsearch
indices.
"""

import argparse
import datetime

from configman import ConfigurationManager

from socorro.external.es.base import generate_list_of_indexes
from socorro.external.es.connection_context import ConnectionContext
from socorro.scripts import WrappedTextHelpFormatter


DESCRIPTION = 'Create and delete Elasticsearch indices'

EPILOG = 'Requires Elasticsearch configuration to be set in environment.'


def get_conn():
    cm = ConfigurationManager(ConnectionContext.get_required_config())
    config = cm.get_config()
    return ConnectionContext(config)


def cmd_create(weeks_past, weeks_future):
    """Create recent indices."""
    conn = get_conn()

    # Create recent indices
    index_name_template = conn.get_index_template()

    # Figure out dates
    today = datetime.date.today()
    from_date = today - datetime.timedelta(weeks=weeks_past)
    to_date = today + datetime.timedelta(weeks=weeks_future)

    # Create indiices
    index_names = generate_list_of_indexes(from_date, to_date, index_name_template)
    for index_name in index_names:
        was_created = conn.create_index(index_name)
        if was_created:
            print('Index %s was created.' % index_name)
        else:
            print('Index %s already existed.' % index_name)


def cmd_list():
    """List indices."""
    conn = get_conn()
    indices_client = conn.indices_client()
    status = indices_client.status()
    indices = status['indices'].keys()
    if indices:
        print('Indices:')
        for index in indices:
            print('   %s' % index)
    else:
        print('No indices.')


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

    subparsers.add_parser('list', help='list indices')

    args = parser.parse_args()

    if args.cmd == 'create':
        return cmd_create(args.past, args.future)

    if args.cmd == 'list':
        return cmd_list()
