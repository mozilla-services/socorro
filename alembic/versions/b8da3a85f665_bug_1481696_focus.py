"""bug 1481696 focus

Revision ID: b8da3a85f665
Revises: 9f7bb4445d7a
Create Date: 2018-08-15 17:30:38.808486

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'b8da3a85f665'
down_revision = '9f7bb4445d7a'


def upgrade():
    op.execute("""
        INSERT INTO products
        (product_name, sort, release_name, rapid_beta_version, rapid_release_version)
        VALUES
        ('Focus', 3, 'focus', 1.0, 1.0)
    """)


def downgrade():
    # There is no downgrade
    pass
