"""Fixes bug 970406 - add raw_adi_logs table

Revision ID: 32b54dec3fc0
Revises: 1ab8d5514ce2
Create Date: 2014-06-12 11:47:19.398882

"""

# revision identifiers, used by Alembic.
revision = '32b54dec3fc0'
down_revision = '1ef041dfc3d5'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

def upgrade():
    op.create_table('raw_adi_logs',
        sa.Column('report_date', sa.DATE(), nullable=True),
        sa.Column('product_name', sa.TEXT(), nullable=True),
        sa.Column('product_os_platform', sa.TEXT(), nullable=True),
        sa.Column('product_os_version', sa.TEXT(), nullable=True),
        sa.Column('product_version', sa.TEXT(), nullable=True),
        sa.Column('build', sa.TEXT(), nullable=True),
        sa.Column('build_channel', sa.TEXT(), nullable=True),
        sa.Column('product_guid', sa.TEXT(), nullable=True),
        sa.Column('count', sa.INTEGER(), nullable=True)
    )

def downgrade():
    op.drop_table('raw_adi_logs')
