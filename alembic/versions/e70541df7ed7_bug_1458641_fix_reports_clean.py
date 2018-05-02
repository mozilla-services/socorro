"""bug 1458641 fix reports clean crontabber app

Revision ID: e70541df7ed7
Revises: 3474e98b321f
Create Date: 2018-05-02 18:20:19.064954

"""

from alembic import op
from socorro.lib.migrations import load_stored_proc


# revision identifiers, used by Alembic.
revision = 'e70541df7ed7'
down_revision = '3474e98b321f'


def upgrade():
    # Note: This should have been done in migration 3474e98b321f.
    load_stored_proc(op, ['001_update_reports_clean.sql'])


def downgrade():
    pass
