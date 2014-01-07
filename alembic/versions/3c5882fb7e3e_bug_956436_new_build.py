"""bug 956436 new build_type, update_channel columns

Revision ID: 3c5882fb7e3e
Revises: 4a6b5fec10e9
Create Date: 2014-01-07 13:40:47.100807

"""

# revision identifiers, used by Alembic.
revision = '3c5882fb7e3e'
down_revision = '4a6b5fec10e9'

from alembic import op
from socorro.lib import citexttype, jsontype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(u'product_build_types',
        sa.Column(u'product_name', sa.citext, nullable=False),
        sa.Column('build_type', postgresql.ENUM(u'release', u'esr', u'aurora', u'beta', u'nightly', name=u'build_type'), nullable=False),
        sa.Column(u'throttle', sa.NUMERIC(), server_default='1.0', nullable=False),
        sa.ForeignKeyConstraint(['product_name'], [u'products.product_name'], ),
        sa.PrimaryKeyConstraint(u'product_name', 'build_type')
    )
    op.add_column(u'product_versions', sa.Column('build_type_enum', postgresql.ENUM(u'release', u'esr', u'aurora', u'beta', u'nightly', name=u'build_type_enum'), server_default=u'release', nullable=False))
    op.add_column(u'raw_adu', sa.Column(u'update_channel', sa.TEXT(), nullable=True))
    op.add_column(u'releases_raw', sa.Column(u'update_channel', sa.TEXT(), nullable=False))
    op.add_column(u'reports', sa.Column(u'update_channel', sa.TEXT(), nullable=True))
    op.add_column(u'reports_clean', sa.Column('build_type', postgresql.ENUM(u'release', u'esr', u'aurora', u'beta', u'nightly', name=u'build_type'), nullable=False))
    op.add_column(u'special_product_platforms', sa.Column('build_type', postgresql.ENUM(u'release', u'esr', u'aurora', u'beta', u'nightly', name=u'build_type'), nullable=False))
    op.add_column(u'tcbs', sa.Column('build_type', postgresql.ENUM(u'release', u'esr', u'aurora', u'beta', u'nightly', name=u'build_type'), nullable=False))
    op.add_column(u'tcbs_build', sa.Column('build_type', postgresql.ENUM(u'release', u'esr', u'aurora', u'beta', u'nightly', name=u'build_type'), nullable=False))

    load_stored_proc(op, ['001_update_reports_clean.sql'])


def downgrade():
    op.drop_column(u'tcbs_build', 'build_type')
    op.drop_column(u'tcbs', 'build_type')
    op.drop_column(u'special_product_platforms', 'build_type')
    op.drop_column(u'reports_clean', 'build_type')
    op.drop_column(u'reports', u'update_channel')
    op.drop_column(u'releases_raw', u'update_channel')
    op.drop_column(u'raw_adu', u'update_channel')
    op.drop_column(u'product_versions', 'build_type_enum')
    op.drop_table(u'product_build_types')

    load_stored_proc(op, ['001_update_reports_clean.sql'])
