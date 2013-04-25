"""bug 855423 change RAISE EXCEPTION to RAISE NOTICE

Revision ID: 5e14d46c725
Revises: e5eb3c07f2a
Create Date: 2013-04-11 17:35:34.174009

"""

# revision identifiers, used by Alembic.
revision = '5e14d46c725'
down_revision = None

from alembic import op
import os

def upgrade():
    # Load up all the new procedures
    app_path=os.getcwd()
    procs = [
		'001_update_reports_clean.sql',
		'add_column_if_not_exists.sql',
		'add_new_product.sql',
		'add_new_release.sql',
		'backfill_matviews.sql',
		'crontabber_nodelete.sql',
		'drop_old_partitions.sql',
		'edit_featured_versions.sql',
		'edit_product_info.sql',
		'update_adu.sql',
		'update_build_adu.sql',
		'update_correlations.sql',
		'update_crashes_by_user_build.sql',
		'update_crashes_by_user.sql',
		'update_daily_crashes.sql',
		'update_explosiveness.sql',
		'update_hang_report.sql',
		'update_home_page_graph_build.sql',
		'update_home_page_graph.sql',
		'update_nightly_builds.sql',
		'update_os_versions.sql',
		'update_rank_compare.sql',
		'update_signatures.sql',
		'update_tcbs_build.sql',
		'update_tcbs.sql',
		'validate_lookup.sql'
    ]
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        proc = open(myfile, 'r').read()
        op.execute(proc)

def downgrade():
    # Tricky. Need to checkout previous revision in repo
    # to do this, so leaving for now.
    return True
