"""drop crontabber_state table

Revision ID: 3860644579f4
Revises: 30adec758cc9
Create Date: 2015-10-16 13:16:04.865018

"""

# revision identifiers, used by Alembic.
revision = '3860644579f4'
down_revision = '30adec758cc9'

from alembic import op


def upgrade():
    op.execute("""
        DROP TABLE crontabber_state
    """)
    op.execute('COMMIT')


def downgrade():  # make travis happy
    op.execute("""
        CREATE TABLE crontabber_state (
            state text NOT NULL,
            last_updated timestamp with time zone NOT NULL
        )
    """)
    op.execute('COMMIT')
