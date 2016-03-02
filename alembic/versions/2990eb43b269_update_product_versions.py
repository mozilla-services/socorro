"""update product versions

Revision ID: 2990eb43b269
Revises: 3860644579f4
Create Date: 2015-12-14 09:55:33.639675

"""

# revision identifiers, used by Alembic.
revision = '2990eb43b269'
down_revision = '3860644579f4'

from alembic import op
from socorrolib.lib.migrations import load_stored_proc


def upgrade():
    load_stored_proc(op, ['update_product_versions.sql'])


def downgrade():
    load_stored_proc(op, ['update_product_versions.sql'])
