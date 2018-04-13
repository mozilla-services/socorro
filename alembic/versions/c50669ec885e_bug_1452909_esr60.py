"""bug 1452909 esr60

Add comm-esr60 and mozilla-esr60 to release repositories.

Revision ID: c50669ec885e
Revises: 7d33170669e2
Create Date: 2018-04-13 16:49:29.121690

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'c50669ec885e'
down_revision = '7d33170669e2'


def upgrade():
    op.execute("""
    INSERT INTO release_repositories VALUES ('mozilla-esr60');
    INSERT INTO release_repositories VALUES ('comm-esr60');
    """)


def downgrade():
    op.execute("""
    DELETE FROM release_repositories WHERE repository = 'mozilla-esr60';
    DELETE FROM release_repositories WHERE repository = 'comm-esr60';
    """)
