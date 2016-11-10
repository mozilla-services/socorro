"""bug 958558 migration for update_product_version() and friends

Revision ID: 2c48009040da
Revises: 48e9a4366530
Create Date: 2014-01-13 12:54:13.988864

"""

# revision identifiers, used by Alembic.
revision = '2c48009040da'
down_revision = '4cacd567770f'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['update_product_versions.sql',
                          'is_rapid_beta.sql',
                          'sunset_date.sql',
                          'update_tcbs.sql'
                          ])


def downgrade():
    load_stored_proc(op, ['update_product_versions.sql',
                          'is_rapid_beta.sql',
                          'sunset_date.sql',
                          'update_tcbs.sql'
                          ])
