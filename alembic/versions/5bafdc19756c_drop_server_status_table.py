"""drop server_status table

Revision ID: 5bafdc19756c
Revises: 89ef86a3d57a
Create Date: 2016-09-13 15:56:53.898014

"""

# revision identifiers, used by Alembic.
revision = '5bafdc19756c'
down_revision = '89ef86a3d57a'

from alembic import op
from socorrolib.lib import citexttype, jsontype, buildtype
from socorrolib.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

from sqlalchemy.dialects import postgresql


def upgrade():
    op.drop_table('server_status')


def downgrade():
    op.create_table('server_status',
    sa.Column('avg_process_sec', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('avg_wait_sec', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('date_created', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('date_oldest_job_queued', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('date_recently_completed', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('processors_count', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('waiting_job_count', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=u'server_status_pkey')
    )
