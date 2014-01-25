"""Fixes bug 963600 - add_new_release() and update_product_versions()

Revision ID: 22ec34ad88fc
Revises: 4bb277899d74
Create Date: 2014-01-24 17:17:06.598669

"""

# revision identifiers, used by Alembic.
revision = '22ec34ad88fc'
down_revision = '4bb277899d74'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.execute("""
        DROP FUNCTION add_new_release(citext, citext, citext, numeric, citext, integer, text, boolean, boolean)
    """)
    load_stored_proc(op, ['add_new_release.sql', 'update_product_versions.sql'])


def downgrade():
    op.execute("""
        DROP FUNCTION add_new_release(citext, citext, citext, numeric, citext, integer, text, text, boolean, boolean)
    """)
    load_stored_proc(op, ['add_new_release.sql', 'udpate_product_versions.sql'])
