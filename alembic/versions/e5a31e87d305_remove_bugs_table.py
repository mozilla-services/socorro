"""remove bugs table

Revision ID: e5a31e87d305
Revises: f8b13d90e22a
Create Date: 2017-08-16 10:37:13.754054

"""

from alembic import op
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import TEXT, INTEGER


# revision identifiers, used by Alembic.
revision = 'e5a31e87d305'
down_revision = 'f8b13d90e22a'


def upgrade():
    op.drop_table('bugs')


def downgrade():
    op.create_table(
        'bugs',
        Column(u'id', INTEGER(), primary_key=True, nullable=False),
        Column(u'status', TEXT()),
        Column(u'resolution', TEXT()),
        Column(u'short_desc', TEXT()),
    )
