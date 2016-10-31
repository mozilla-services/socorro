"""reload sunset_date function

Revision ID: 495e6c766315
Revises: 5bafdc19756c
Create Date: 2016-10-31 12:46:22.476356

"""

from alembic import op
from socorrolib.lib.migrations import load_stored_proc

# revision identifiers, used by Alembic.
revision = '495e6c766315'
down_revision = '5bafdc19756c'


def upgrade():
    load_stored_proc(op, ['sunset_date.sql'])


def downgrade():
    pass
