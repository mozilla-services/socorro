"""Adding raw_crashes and raw_adu.received_at

Revision ID: 5316d4cfc03a
Revises: None
Create Date: 2013-03-26 11:30:19.464380

"""

# revision identifiers, used by Alembic.
revision = '5316d4cfc03a'
down_revision = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from socorro.external.postgresql.models import JSON

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table(u'raw_crashes',
    sa.Column(u'uuid', postgresql.UUID(), nullable=False, index=True, unique=True),
    sa.Column(u'raw_crash', JSON(), nullable=False),
    sa.Column(u'date_processed', postgresql.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(u'raw_adu', sa.Column(u'received_at', postgresql.TIMESTAMP(timezone=True), server_default='NOW()', nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column(u'raw_adu', u'received_at')
    op.drop_table(u'raw_crashes')
    ### end Alembic commands ###
