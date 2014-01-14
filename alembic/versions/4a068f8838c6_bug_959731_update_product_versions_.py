"""bug 959731 update_product_versions() refresh

Revision ID: 4a068f8838c6
Revises: 2c48009040da
Create Date: 2014-01-14 12:42:25.587189

"""

# revision identifiers, used by Alembic.
revision = '4a068f8838c6'
down_revision = '514789372d99'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['update_product_versions.sql'])


def downgrade():
    load_stored_proc(op, ['update_product_versions.sql'])
