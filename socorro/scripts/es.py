# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Elasticsearch manipulation script for deleting and creating Elasticsearch
indices.
"""

import datetime
import json

import click
from configman import ConfigurationManager
from configman.environment import environment
from elasticsearch_dsl import Search
from elasticsearch.client import IndicesClient

from socorro.external.es.base import generate_list_of_indexes
from socorro.external.es.connection_context import ConnectionContext


def get_conn():
    # Create a configuration manager that will only check the environment for
    # configuration and not command line parameters

    cm = ConfigurationManager(
        ConnectionContext.get_required_config(), values_source_list=[environment]
    )
    config = cm.get_config()
    return ConnectionContext(config)


@click.group()
def es_group():
    """Create and delete Elasticsearch indices.

    Requires Elasticsearch configuration to be set in environment.

    """


@es_group.command("create")
@click.option(
    "--weeks-future",
    type=int,
    default=2,
    help="Number of weeks in the future to create.",
)
@click.option(
    "--weeks-past", type=int, default=2, help="Number of weeks in the future to create."
)
@click.pass_context
def cmd_create(ctx, weeks_future, weeks_past):
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
            click.echo("Index %s was created." % index_name)
        else:
            click.echo("Index %s already existed." % index_name)


@es_group.command("list")
@click.pass_context
def cmd_list(ctx):
    """List indices."""
    conn = get_conn()
    indices = conn.get_indices()
    if indices:
        click.echo("Indices:")
        for index in indices:
            click.echo("   %s" % index)
    else:
        click.echo("No indices.")


@es_group.command("list_crashids")
@click.argument("index", nargs=1)
@click.pass_context
def cmd_list_crashids(ctx, index):
    """List crashids for index."""
    es_conn = get_conn()
    with es_conn() as conn:
        search = Search(
            using=conn,
            index=index,
            doc_type=es_conn.get_doctype(),
        )
        search = search.fields("processed_crash.uuid")
        results = search.execute()
        click.echo("Crashids in %s:" % index)
        for hit in results:
            click.echo(hit["processed_crash.uuid"][0])


@es_group.command("print_mapping")
@click.argument("index", nargs=1)
@click.pass_context
def cmd_print_mapping(ctx, index):
    context = get_conn()
    doctype = context.get_doctype()
    conn = context.connection()
    indices_client = IndicesClient(conn)
    resp = indices_client.get_mapping(index=index)
    mapping = resp[index]["mappings"][doctype]["properties"]
    click.echo(json.dumps(mapping, indent=2, sort_keys=True))


@es_group.command("print_document")
@click.argument("index", nargs=1)
@click.argument("crashid", nargs=1)
@click.pass_context
def cmd_print_document(ctx, index, crashid):
    context = get_conn()
    conn = context.connection()
    search = Search(
        using=conn,
        index=index,
        doc_type=context.get_doctype(),
    )
    search = search.query("match", crash_id=crashid)
    results = search.execute()
    for item in results:
        click.echo(json.dumps(item.to_dict(), indent=2, sort_keys=True))


@es_group.command("delete")
@click.argument("index", required=False)
@click.pass_context
def cmd_delete(ctx, index):
    """Delete indices."""
    conn = get_conn()
    if index:
        indices_to_delete = [index]
    else:
        indices_to_delete = conn.get_indices()

    if not indices_to_delete:
        click.echo("No indices to delete.")
        return

    for index_name in indices_to_delete:
        conn.delete_index(index_name)
        click.echo("Deleted index: %s" % index_name)


if __name__ == "__main__":
    es_group()
