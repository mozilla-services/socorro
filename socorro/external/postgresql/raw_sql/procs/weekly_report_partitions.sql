CREATE OR REPLACE FUNCTION weekly_report_partitions(numweeks integer DEFAULT 2, targetdate timestamp with time zone DEFAULT NULL::timestamp with time zone) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- this function checks that we have partitions two weeks into
-- the future for each of the tables associated with
-- reports
-- designed to be called as a cronjob once a week
-- controlled by the data in the reports_partition_info table
DECLARE
    thisweek DATE;
    dex INT := 1;
    weeknum INT := 0;
    tabinfo RECORD;
BEGIN
    targetdate := COALESCE(targetdate, now());
    thisweek := date_trunc('week', targetdate)::date;

    WHILE weeknum <= numweeks LOOP
        FOR tabinfo IN SELECT * FROM report_partition_info
            ORDER BY build_order LOOP

            PERFORM create_weekly_partition (
                tablename := tabinfo.table_name,
                theweek := thisweek,
                uniques := tabinfo.keys,
                indexes := tabinfo.indexes,
                fkeys := tabinfo.fkeys,
                tableowner := 'breakpad_rw',
                partcol := tabinfo.partition_column,
                timetype := tabinfo.timetype
            );

        END LOOP;
        weeknum := weeknum + 1;
        thisweek := thisweek + 7;
    END LOOP;

    RETURN TRUE;

END; $$;
