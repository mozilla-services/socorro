"""add reasons foreign key to correlations

Revision ID: a44fb7695c10
Revises: 373ef4569b93
Create Date: 2016-05-10 09:02:08.516523

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a44fb7695c10'
down_revision = '373ef4569b93'


def upgrade():
    op.drop_index('correlations_signature_idx', table_name='correlations')
    op.add_column(
        'correlations', sa.Column('reason_id', sa.INTEGER(), nullable=True)
    )
    op.create_index(
        'correlations_signature_idx',
        'correlations',
        [
            'product_version_id',
            'platform',
            'key',
            'date',
            'signature_id',
            'reason_id',
        ],
        unique=True,
    )


def downgrade():
    op.drop_column(
        'correlations', 'reason_id'
    )
    op.create_index(
        'correlations_signature_idx',
        'correlations',
        [
            'product_version_id',
            'platform',
            'key',
            'date',
            'signature_id',
        ],
        unique=True,
    )
