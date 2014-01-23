"""Add version_build column

Revision ID: 4bb277899d74
Revises: 355d0795af7f
Create Date: 2014-01-23 15:37:08.692426

"""

# revision identifiers, used by Alembic.
revision = '4bb277899d74'
down_revision = '355d0795af7f'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.add_column(u'product_versions', sa.Column(u'version_build', sa.TEXT(), nullable=True))
    op.add_column(u'releases_raw', sa.Column(u'version_build', sa.TEXT(), nullable=True))


def downgrade():
    op.drop_column(u'releases_raw', u'version_build')
    op.drop_column(u'product_versions', u'version_build')
