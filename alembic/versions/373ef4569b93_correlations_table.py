"""correlations table

Revision ID: 373ef4569b93
Revises: 335c2bfd99a6
Create Date: 2016-04-25 14:11:28.373859

"""

from alembic import op
import sqlalchemy as sa

from socorrolib.lib import jsontype

# revision identifiers, used by Alembic.
revision = '373ef4569b93'
down_revision = '335c2bfd99a6'


def upgrade():
    op.create_table(
        'correlations',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column(
            'product_version_id',
            sa.INTEGER(),
            autoincrement=False,
            nullable=False
        ),
        sa.Column('platform', sa.TEXT(), nullable=False),
        sa.Column('signature_id', sa.INTEGER(), nullable=False),
        sa.Column('key', sa.TEXT(), nullable=False),
        sa.Column(
            'count',
            sa.INTEGER(),
            server_default=sa.text(u'0'),
            nullable=False
        ),
        sa.Column('notes', sa.TEXT(), server_default=u'', nullable=False),
        sa.Column('date', sa.DATE(), nullable=False),
        sa.Column('payload', jsontype.JsonType(), nullable=True),
        sa.PrimaryKeyConstraint('id', 'platform')
    )
    op.create_index(
        'correlations_signature_idx',
        'correlations',
        [
            'product_version_id',
            'platform',
            'key',
            'date',
            'signature_id'
        ],
    )
    op.create_index(
        'correlations_signatures_idx',
        'correlations',
        [
            'product_version_id',
            'platform',
            'key',
            'date'
        ],
    )


def downgrade():
    op.drop_index('correlations_signatures_idx', table_name='correlations')
    op.drop_index('correlations_signature_idx', table_name='correlations')
    op.drop_table('correlations')
