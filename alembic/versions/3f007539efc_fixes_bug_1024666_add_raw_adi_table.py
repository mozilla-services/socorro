"""Fixes bug 1024666 - add raw_adi table

Revision ID: 3f007539efc
Revises: 32b54dec3fc0
Create Date: 2014-06-13 09:38:29.347397

"""

# revision identifiers, used by Alembic.
revision = '3f007539efc'
down_revision = '32b54dec3fc0'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('raw_adi',
        sa.Column('adi_count', sa.INTEGER(), nullable=True),
        sa.Column('date', sa.DATE(), nullable=True),
        sa.Column('product_name', sa.TEXT(), nullable=True),
        sa.Column('product_os_platform', sa.TEXT(), nullable=True),
        sa.Column('product_os_version', sa.TEXT(), nullable=True),
        sa.Column('product_version', sa.TEXT(), nullable=True),
        sa.Column('build', sa.TEXT(), nullable=True),
        sa.Column('product_guid', sa.TEXT(), nullable=True),
        sa.Column('update_channel', sa.TEXT(), nullable=True),
        sa.Column('received_at', postgresql.TIMESTAMP(timezone=True), server_default='NOW()', nullable=True)
    )
    op.create_index('raw_adi_1_idx', 'raw_adi', ['date', 'product_name', 'product_version', 'product_os_platform', 'product_os_version'], unique=False)


def downgrade():
    op.drop_index('raw_adi_1_idx', table_name='raw_adi')
    op.drop_table('raw_adi')
