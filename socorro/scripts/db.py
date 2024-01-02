# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Manipulate local db.

# Usage: ./bin/db.py CMD

import os
from urllib.parse import urlsplit

import click
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def get_dsn():
    return os.environ.get("DATABASE_URL")


@click.group()
def db_group():
    """Local dev environment DB manipulation script.

    DATABASE_URL is required to be set in the environment.

    """


@db_group.command("create")
@click.pass_context
def create_database(ctx):
    dsn = get_dsn()
    if not dsn:
        raise click.ClickException("DATABASE_URL is not defined in environment")

    parsed = urlsplit(dsn)
    db_name = parsed.path[1:]
    adjusted_dsn = dsn[: -(len(db_name) + 1)]

    conn = psycopg2.connect(adjusted_dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    try:
        cursor.execute("CREATE DATABASE %s" % db_name)
        click.echo('Created database "%s".' % db_name)
    except psycopg2.ProgrammingError:
        click.echo('Database "%s" already exists.' % db_name)
        return 1


@db_group.command("drop")
@click.pass_context
def drop_database(ctx):
    dsn = get_dsn()
    if not dsn:
        raise click.ClickException("DATABASE_URL is not defined in environment")

    parsed = urlsplit(dsn)
    db_name = parsed.path[1:]
    adjusted_dsn = dsn[: -(len(db_name) + 1)]

    conn = psycopg2.connect(adjusted_dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    try:
        cursor.execute("DROP DATABASE %s" % db_name)
        click.echo('Database "%s" dropped.' % db_name)
    except psycopg2.ProgrammingError:
        click.echo('Database "%s" does not exist.' % db_name)
        return 1


if __name__ == "__main__":
    db_group()
