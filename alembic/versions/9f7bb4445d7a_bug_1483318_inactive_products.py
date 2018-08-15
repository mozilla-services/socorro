"""bug 1483318 inactive products

Fix sort for all products so that inactive products have a sort of -1 and
active products have an appropriate sort number that gives us room to add new
products without having to futz with sort numbers.

Revision ID: 9f7bb4445d7a
Revises: eb8269f6bb85
Create Date: 2018-08-15 13:46:36.219981

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '9f7bb4445d7a'
down_revision = 'eb8269f6bb85'


def upgrade():
    # First set everything to -1 making it all inactive.
    op.execute("""
        UPDATE products
        SET sort = -1
    """)

    # Then set active products to appropriate sort numbers.
    to_set = [
        # These are key products
        ('Firefox', 1),
        ('FennecAndroid', 2),

        # These are products that are in the system, but unsupported; we
        # leave some room so we can add products between
        ('Thunderbird', 80),
        ('SeaMonkey', 90),

        # This is an anomly that probably shouldn't show up and we need to
        # figure out how to fix it
        ('Fennec', 100),
    ]
    for product_name, sort_number in to_set:
        op.execute("""
            UPDATE products
            SET sort = %s
            WHERE product_name = '%s'
        """ % (sort_number, product_name)
        )


def downgrade():
    # There is no going back--only forward
    pass
