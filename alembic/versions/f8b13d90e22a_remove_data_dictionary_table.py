"""remove data_dictionary table

Revision ID: f8b13d90e22a
Revises: 15d9132d759e
Create Date: 2017-08-15 14:15:08.960047

"""
from alembic import op
from sqlalchemy import types, Column
from sqlalchemy.dialects.postgresql import TEXT

# revision identifiers, used by Alembic.
revision = 'f8b13d90e22a'
down_revision = '15d9132d759e'


class JSON(types.UserDefinedType):
    name = 'json'

    def get_col_spec(self):
        return 'JSON'

    def bind_processor(self, dialect):
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

    def __repr__(self):
        return "json"


def upgrade():
    op.drop_table('data_dictionary')


def downgrade():
    op.create_table(
        'data_dictionary',
        Column(u'raw_field', TEXT(), nullable=False, primary_key=True),
        Column(u'transforms', JSON()),
        Column(u'product', TEXT())
    )
