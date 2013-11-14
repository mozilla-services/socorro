"""Adding duration

Revision ID: 4aacaea3eb48
Revises: 477e1c6e6df3
Create Date: 2013-11-07 11:33:42.125557

"""

# revision identifiers, used by Alembic.
revision = '4aacaea3eb48'
down_revision = '477e1c6e6df3'

from alembic import op
from socorro.lib import citexttype, jsontype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    op.add_column(u'crontabber_log', sa.Column(u'duration', sa.INTERVAL(), nullable=True))


def downgrade():
    op.drop_column(u'crontabber_log', u'duration')
