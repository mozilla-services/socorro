"""Fixes bug 1122145 add release repos for fennec

Revision ID: 2cdb9abe6291
Revises: 5387d590bc45
Create Date: 2015-01-16 11:18:40.881952

"""

# revision identifiers, used by Alembic.
revision = '2cdb9abe6291'
down_revision = '445fefe2e08f'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.execute("""
        INSERT INTO release_repositories
        VALUES
        ('mozilla-central-android-api-11'),
        ('mozilla-aurora-android-api-11')
    """)


def downgrade():
    op.execute("""
        DELETE FROM release_repositories
        WHERE repository IN
        ('mozilla-central-android-api-11', 'mozilla-aurora-android-api-11')
    """)
