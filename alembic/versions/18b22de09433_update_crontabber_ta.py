"""Update crontabber table permissions

Revision ID: 18b22de09433
Revises: 4c7a28212f15
Create Date: 2013-11-04 13:30:38.984447

"""

# revision identifiers, used by Alembic.
revision = '18b22de09433'
down_revision = '4c7a28212f15'

from alembic import op
from socorro.lib import citexttype, jsontype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    fix_permissions(op, 'crontabber')
    fix_permissions(op, 'crontabber_log')


def downgrade():
    # NO TURNING BACK
    pass
