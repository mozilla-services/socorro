"""removed foreign key between bug_associations and bugs

Revision ID: a5e0f0bc87d6
Revises: 495e6c766315
Create Date: 2017-05-29 19:17:39.607018

"""

# revision identifiers, used by Alembic.
revision = 'a5e0f0bc87d6'
down_revision = '495e6c766315'

from alembic import op


def upgrade():
    op.drop_constraint(
        'bug_associations_bug_id_fkey',
        'bug_associations',
        type_='foreignkey'
    )


def downgrade():
    op.create_foreign_key(
        'bug_associations_bug_id_fkey',
        'bug_associations',
        'bugs',
        ['bug_id'],
        ['id'],
    )
