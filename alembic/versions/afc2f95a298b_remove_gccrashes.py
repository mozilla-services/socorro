"""remove gccrashes

Revision ID: afc2f95a298b
Revises: 77395783fce5
Create Date: 2017-08-29 14:21:59.825946

"""

from alembic import op
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import INTEGER, NUMERIC, REAL, TIMESTAMP

from socorro.lib.migrations import load_stored_proc


# revision identifiers, used by Alembic.
revision = 'afc2f95a298b'
down_revision = '77395783fce5'


def upgrade():
    op.execute(
        'DROP FUNCTION update_gccrashes(date, boolean, interval)'
    )
    op.execute(
        'DROP FUNCTION backfill_gccrashes(date, interval)'
    )
    op.drop_table('gccrashes')
    load_stored_proc(op, ['backfill_matviews.sql'])


def downgrade():
    """
    Because the writing of this migration coincides with the removal of
    raw_sql/procs/update_gccrashes.sql and raw_sql/procs/backfill_gccrashes.sql
    we can't rely on loading those files from disc.
    So for the downgrade we'll just simply re-execute the necessary SQL.
    """
    op.create_table(
        'gccrashes',
        Column(u'report_date', TIMESTAMP(timezone=True), nullable=False),
        Column(u'product_version_id', INTEGER(), nullable=False),
        Column(u'build', NUMERIC(), nullable=True),
        Column(u'gc_count_madu', REAL(), nullable=False),
    )
    op.execute("""
        CREATE OR REPLACE FUNCTION backfill_gccrashes(
            updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
            LANGUAGE plpgsql
            AS $$
        BEGIN
        -- function for administrative backfilling of gccrashes
        -- designed to be called by backfill_matviews
        DELETE FROM gccrashes WHERE report_date = updateday;
        PERFORM update_gccrashes(updateday, false, check_period);

        RETURN TRUE;
        END;$$;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_gccrashes(
            updateday date,
            checkdata boolean DEFAULT true,
            check_period interval DEFAULT '01:00:00'::interval
        ) RETURNS boolean
            LANGUAGE plpgsqlq
            SET client_min_messages TO 'ERROR'
        AS $$
        BEGIN
        -- this procedure goes through raw crashes and creates a matview with count of
        -- is_gc annotated crashes per build ID
        -- designed to be run only once for each day

        -- check that it hasn't already been run

        IF checkdata THEN
            PERFORM 1 FROM gccrashes
            WHERE report_date = updateday LIMIT 1;
            IF FOUND THEN
                RAISE NOTICE 'gccrashes has already been run for the day %.',updateday;
                RETURN FALSE;
            END IF;
        END IF;

        -- check if reports_clean is complete
        IF NOT reports_clean_done(updateday, check_period) THEN
            IF checkdata THEN
                RAISE NOTICE 'Reports_clean has not been updated to the end of %',updateday;
                RETURN FALSE;
            ELSE
                RAISE INFO 'reports_clean not updated';
                RETURN FALSE;
            END IF;
        END IF;

        INSERT INTO gccrashes (
            report_date,
            product_version_id,
            build,
            gc_count_madu
        )
        WITH raw_crash_filtered AS (
            SELECT
                  uuid
                , json_object_field_text(r.raw_crash, 'IsGarbageCollecting')
                as is_garbage_collecting
            FROM
                raw_crashes r
            WHERE
                date_processed BETWEEN updateday::timestamptz
                    AND updateday::timestamptz + '1 day'::interval
        )
        SELECT updateday
            , product_version_id
            , build
            , crash_madu(sum(
                CASE WHEN r.is_garbage_collecting = '1' THEN 1 ELSE 0 END), sum(adu_count), 1
            ) as gc_count_madu
        FROM reports_clean
            JOIN product_versions USING (product_version_id)
            JOIN build_adu USING (product_version_id)
            LEFT JOIN raw_crash_filtered r ON r.uuid::text = reports_clean.uuid
        WHERE utc_day_is(date_processed, updateday)
                AND tstz_between(date_processed, build_date(build), sunset_date)
                AND product_versions.build_type = 'nightly'
                AND tstz_between(adu_date, build_date(build), sunset_date)
                AND adu_count > 0
                AND build_date(build) = build_adu.build_date
                AND date_processed - build_date(build) < '7 days'::interval
                AND length(build::text) >= 10
        GROUP BY build, product_version_id
        ORDER BY build;

        RETURN TRUE;
        END;
        $$;
    """)

    load_stored_proc(op, ['backfill_matviews.sql'])
