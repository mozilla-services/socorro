"""remove explosiveness remnants

Revision ID: 77395783fce5
Revises: e5a31e87d305
Create Date: 2017-08-28 13:58:03.355534

"""
from alembic import op
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import INTEGER, NUMERIC, DATE


# revision identifiers, used by Alembic.
revision = '77395783fce5'
down_revision = 'e5a31e87d305'


def upgrade():
    op.drop_table('explosiveness')


def downgrade():
    """
        CREATE TABLE explosiveness (
            product_version_id integer NOT NULL,
            signature_id integer NOT NULL,
            last_date date NOT NULL,
            oneday numeric,
            threeday numeric,
            day0 numeric,
            day1 numeric,
            day2 numeric,
            day3 numeric,
            day4 numeric,
            day5 numeric,
            day6 numeric,
            day7 numeric,
            day8 numeric,
            day9 numeric
        )
    """
    op.create_table(
        'explosiveness',
        Column(u'day0', NUMERIC()),
        Column(u'day1', NUMERIC()),
        Column(u'day2', NUMERIC()),
        Column(u'day3', NUMERIC()),
        Column(u'day4', NUMERIC()),
        Column(u'day5', NUMERIC()),
        Column(u'day6', NUMERIC()),
        Column(u'day7', NUMERIC()),
        Column(u'day8', NUMERIC()),
        Column(u'day9', NUMERIC()),
        Column(
            u'last_date',
            DATE(),
            primary_key=True,
            nullable=False
        ),
        Column(u'oneday', NUMERIC()),
        Column(
            u'product_version_id',
            INTEGER(),
            primary_key=True,
            nullable=False,
            autoincrement=False,
            index=True
        ),
        Column(
            u'signature_id',
            INTEGER(),
            primary_key=True,
            nullable=False,
            index=True
        ),
        Column(u'threeday', NUMERIC())
    )
