"""extend missing symbols

Revision ID: 89ef86a3d57a
Revises: 02da1335e26e
Create Date: 2016-05-26 13:17:17.145484

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '89ef86a3d57a'
down_revision = '02da1335e26e'


def upgrade():
    op.add_column(
        'missing_symbols',
        sa.Column(
            'code_file',
            sa.TEXT(),
            nullable=True,
        )
    )
    op.add_column(
        'missing_symbols',
        sa.Column(
            'code_id',
            sa.TEXT(),
            nullable=True,
        )
    )


def downgrade():
    op.drop_column('missing_symbols', 'code_file')
    op.drop_column('missing_symbols', 'code_id')
