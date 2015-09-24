"""delete nightly_builds from crontabber state

Revision ID: 4350f1383a9b
Revises: b91ff5f1954
Create Date: 2015-09-21 15:10:04.834907

"""

# revision identifiers, used by Alembic.
revision = '4350f1383a9b'
down_revision = 'b91ff5f1954'

from alembic import op


def upgrade():
    op.execute("""
        DELETE FROM crontabber WHERE app_name = 'nightly-builds-matview'
    """)
    op.execute('COMMIT')


def downgrade():
    pass
