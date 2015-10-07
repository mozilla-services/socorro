"""drop lag_log table

Revision ID: 30adec758cc9
Revises: 4350f1383a9b
Create Date: 2015-10-06 11:39:19.353086

"""

# revision identifiers, used by Alembic.
revision = '30adec758cc9'
down_revision = '4350f1383a9b'

from alembic import op


def upgrade():
    op.execute("""
        DROP TABLE lag_log
    """)
    op.execute('COMMIT')


def downgrade():
    op.execute("""
        CREATE TABLE lag_log (
            replica_name text NOT NULL,
            moment timestamp with time zone NOT NULL,
            lag integer NOT NULL,
            master text NOT NULL
        )
    """)
    op.execute('COMMIT')
