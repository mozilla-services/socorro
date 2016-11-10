"""bug 917823 - remove 7day constraint on builds in aggregates

Revision ID: 122bac0f6ade
Revises: 3c5882fb7e3e
Create Date: 2014-01-09 15:14:45.727825

"""

# revision identifiers, used by Alembic.
revision = '122bac0f6ade'
down_revision = '3c5882fb7e3e'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(
        op, [
        'update_crashes_by_user_build.sql',
        'update_home_page_graph_build.sql',
        'update_tcbs_build.sql'
    ])


def downgrade():
    load_stored_proc(
        op, [
        'update_crashes_by_user_build.sql',
        'update_home_page_graph_build.sql',
        'update_tcbs_build.sql'
    ])
