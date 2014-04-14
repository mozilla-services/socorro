CREATE OR REPLACE FUNCTION backfill_weekly_report_partitions(
        startweek DATE,
        endweek DATE,
        tablename TEXT)
    RETURNS boolean
    LANGUAGE plpgsql
AS $$
--
-- backfill_weekly_report_partitions(startweek, endweek, tablename)
-- Creates partitions for an arbitrary range of time.
-- Controlled by the data in the reports_partition_info table
--
DECLARE
    thisweek DATE;
    tabinfo RECORD;
BEGIN
    thisweek := date_trunc('week', startweek)::date;

    SELECT INTO tabinfo * FROM report_partition_info
        WHERE table_name = tablename LIMIT 1;

    WHILE thisweek <= endweek LOOP
        PERFORM create_weekly_partition (
            tablename := tabinfo.table_name,
            theweek := thisweek,
            uniques := tabinfo.keys,
            indexes := tabinfo.indexes,
            fkeys := tabinfo.fkeys,
            tableowner := 'breakpad_rw',
            partcol := tabinfo.partition_column
        );
        thisweek := thisweek + 7;
    END LOOP;

    RETURN TRUE;
END; $$;

