"""Remove unused skiplist table.

Revision ID: 02da1335e26e
Revises: 373ef4569b93
Create Date: 2016-05-19 11:52:00.068995

"""

from alembic import op

import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '02da1335e26e'
down_revision = '373ef4569b93'


def upgrade():
    op.drop_table(u'skiplist')


def downgrade():
    op.create_table(
        u'skiplist',
        sa.Column(u'category', sa.TEXT(), nullable=False),
        sa.Column(u'rule', sa.TEXT(), nullable=False),
        sa.PrimaryKeyConstraint(u'category', u'rule')
    )
