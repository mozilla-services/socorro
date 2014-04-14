"""bug 826564 - add signature column

Revision ID: 8894c185715
Revises: 9798b1cc04
Create Date: 2013-06-06 11:57:23.846326

"""

# revision identifiers, used by Alembic.
revision = '8894c185715'
down_revision = '9798b1cc04'

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import types
from sqlalchemy.sql import table, column
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column(u'exploitability_reports', sa.Column(u'signature', sa.TEXT(), nullable=False))


def downgrade():
    op.drop_column(u'exploitability_reports', u'signature')
