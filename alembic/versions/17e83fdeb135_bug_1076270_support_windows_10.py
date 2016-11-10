"""bug 1076270 - support windows 10

Revision ID: 17e83fdeb135
Revises: 52dbc7357409
Create Date: 2014-10-03 14:03:29.837940

"""

# revision identifiers, used by Alembic.
revision = '17e83fdeb135'
down_revision = '52dbc7357409'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.execute("""
        UPDATE os_versions
        SET os_version_string = 'Windows 10'
        WHERE major_version = 6
        AND minor_version = 4
        AND os_name = 'Windows'
    """)


def downgrade():
    op.execute("""
        UPDATE os_versions
        SET os_version_string = 'Windows Unknown'
        WHERE major_version = 6
        AND minor_version = 4
        AND os_name = 'Windows Unknown'
    """)
