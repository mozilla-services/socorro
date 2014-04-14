"""index on report_date on exploitability_reports

Revision ID: 471c6efadde
Revises: 3e70bfd1ab0c
Create Date: 2013-07-02 13:20:10.895872

By: peterbe
"""

# revision identifiers, used by Alembic.
revision = '471c6efadde'
down_revision = '3e70bfd1ab0c'

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import types
from sqlalchemy.sql import table, column

def upgrade():
    op.create_index('exploitability_report_date_idx', 'exploitability_reports', ['report_date'])

def downgrade():
    op.drop_index('exploitability_report_date_idx')
