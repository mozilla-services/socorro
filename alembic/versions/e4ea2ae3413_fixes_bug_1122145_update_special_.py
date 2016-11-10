"""Fixes bug 1122145 update special_product_platforms

Revision ID: e4ea2ae3413
Revises: 1023855cf1ad
Create Date: 2015-01-20 08:29:29.560081

"""

# revision identifiers, used by Alembic.
revision = 'e4ea2ae3413'
down_revision = '1023855cf1ad'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    # updated documentation for update_product_versions
    load_stored_proc(op, ['update_product_versions.sql'])
    # insert new fennec repos into special_product_platforms
    op.execute("""
        INSERT INTO special_product_platforms
            (platform, repository, release_channel, release_name, product_name, min_version)
        VALUES
            ('android-arm', 'mozilla-central-android-api-11', 'nightly', 'mobile', 'FennecAndroid', '37.0'),
            ('android-arm', 'mozilla-aurora-android-api-11', 'aurora', 'mobile', 'FennecAndroid', '37.0')
    """)


def downgrade():
    load_stored_proc(op, ['update_product_versions.sql'])
    op.execute("""
        DELETE FROM special_product_platforms
        WHERE repository IN ('mozilla-central-android-api-11', 'mozilla-aurora-android-api-11')
    """)
