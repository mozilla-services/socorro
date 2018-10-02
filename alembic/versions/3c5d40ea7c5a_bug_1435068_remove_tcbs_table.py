"""bug 1435068 remove tcbs and tcbs_build table

Revision ID: 3c5d40ea7c5a
Revises: 0f31c225e765
Create Date: 2018-02-07 20:19:35.990596

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '3c5d40ea7c5a'
down_revision = '0f31c225e765'


def upgrade():
    # Delete the tcbs_build and tcbs tables
    op.execute("""
        DROP TABLE IF EXISTS tcbs
    """)
    op.execute("""
        DROP TABLE IF EXISTS tcbs_build
    """)


def downgrade():
    # There is no going back.
    pass
