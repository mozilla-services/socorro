"""Fixes bug 1047079 - remove processors, jobs tables

Revision ID: 235c80dc2e12
Revises: 556e11f2d00f
Create Date: 2014-12-30 13:29:15.108296

"""

# revision identifiers, used by Alembic.
revision = '235c80dc2e12'
down_revision = '556e11f2d00f'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.drop_table('jobs')
    op.drop_table('processors')
    op.alter_column('server_status', 'processors_count', nullable=True)


def downgrade():
    op.alter_column('server_status', 'processors_count', nullable=False)
    op.execute("""
        CREATE TABLE processors (
            id serial NOT NULL PRIMARY KEY,
            name varchar(255) NOT NULL UNIQUE,
            startdatetime timestamp with time zone NOT NULL,
            lastseendatetime timestamp with time zone
        )
    """)
    op.execute("""
        CREATE TABLE jobs (
            id serial NOT NULL PRIMARY KEY,
            pathname character varying(1024) NOT NULL,
            uuid varchar(50) NOT NULL UNIQUE,
            owner integer,
            priority integer DEFAULT 0,
            queueddatetime timestamp with time zone,
            starteddatetime timestamp with time zone,
            completeddatetime timestamp with time zone,
            success boolean,
            message text,
            FOREIGN KEY (owner) REFERENCES processors (id)
        )
    """)
    op.execute("""
        CREATE INDEX jobs_owner_key ON jobs (owner)
    """)
    op.execute("""
        CREATE INDEX jobs_owner_starteddatetime_key ON jobs (owner, starteddatetime)
    """)
    op.execute("""
        CREATE INDEX jobs_owner_starteddatetime_priority_key ON jobs (owner, starteddatetime, priority DESC)
    """)
    op.execute("""
        CREATE INDEX jobs_completeddatetime_queueddatetime_key ON jobs (completeddatetime, queueddatetime)
    """)
