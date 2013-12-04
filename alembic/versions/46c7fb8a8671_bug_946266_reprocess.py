"""bug 946266 reprocessing table

Revision ID: 46c7fb8a8671
Revises: 3a5471a358bf
Create Date: 2013-12-04 08:17:58.348462

"""

# revision identifiers, used by Alembic.
revision = '46c7fb8a8671'
down_revision = '3a5471a358bf'

from alembic import op
from socorro.lib import citexttype, jsontype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(u'reprocessing_jobs',
    sa.Column(u'crash_id', postgresql.UUID(), nullable=True),
    )

def downgrade():
    op.drop_table(u'reprocessing_jobs')
