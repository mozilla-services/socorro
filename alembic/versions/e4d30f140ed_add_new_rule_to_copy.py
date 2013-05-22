"""Add new rule to copy Plugin url and comment

Revision ID: e4d30f140ed
Revises: 22e4e60e03f
Create Date: 2013-05-22 08:01:54.873655

"""

# revision identifiers, used by Alembic.
revision = 'e4d30f140ed'
down_revision = '22e4e60e03f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlalchemy.types as types
from sqlalchemy.sql import table, column

class CITEXT(types.UserDefinedType):
    name = 'citext'

    def get_col_spec(self):
        return 'CITEXT'

    def bind_processor(self, dialect):
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

    def __repr__(self):
        return "citext"


def upgrade():
    transform_rule = table('transform_rules',
        column(u'transform_rule_id', sa.INTEGER()),
        column(u'category', CITEXT()),
        column(u'rule_order', sa.INTEGER()),
        column(u'action', sa.TEXT()),
        column(u'action_args', sa.TEXT()),
        column(u'action_kwargs', sa.TEXT()),
        column(u'predicate', sa.TEXT()),
        column(u'predicate_args', sa.TEXT()),
        column(u'predicate_kwargs', sa.TEXT()))

        # Indexes
    op.bulk_insert(transform_rule, [{
        "category": 'processor.json_rewrite'
        , "predicate": 'socorro.lib.transform_rules.is_not_null_predicate'
        , "predicate_args": ''
        , "predicate_kwargs": 'key="PluginContentURL"'
        , "action": 'socorro.processor.processor.json_reformat_action'
        , "action_args": ''
        , "action_kwargs": 'key="URL", format_str="%(PluginContentURL)s"'
        , "rule_order": '5'
    }, {
        "category": 'processor.json_rewrite'
        , "predicate": 'socorro.lib.transform_rules.is_not_null_predicate'
        , "predicate_args": ''
        , "predicate_kwargs": 'key="PluginUserComment"'
        , "action": 'socorro.processor.processor.json_reformat_action'
        , "action_args": ''
        , "action_kwargs": 'key="Comments", format_str="%(PluginUserComment)s"'
        , "rule_order": '6'
    }])

def downgrade():
    op.execute("""
        DELETE from transform_rules
        where action_kwargs IN
        ('key="Comments", format_str="%(PluginUserComment)s"'
        , 'key="URL", format_str="%(PluginContentURL)s"');
    """)
