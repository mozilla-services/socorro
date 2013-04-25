CREATE OR REPLACE FUNCTION backfill_reports_clean(begin_time timestamp with time zone, end_time timestamp with time zone DEFAULT NULL::timestamp with time zone) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- administrative utility for backfilling reports_clean to the selected date
-- intended to be called on the command line
-- uses a larger cycle (6 hours) if we have to backfill several days of data
-- note that this takes timestamptz as parameters
-- otherwise call backfill_reports_clean_by_date.
DECLARE cyclesize INTERVAL := '1 hour';
	stop_time timestamptz;
	cur_time timestamptz := begin_time;
BEGIN
	IF end_time IS NULL OR end_time > ( now() - interval '3 hours' ) THEN
	-- if no end time supplied, then default to three hours ago
	-- on the hour
		stop_time := ( date_trunc('hour', now()) - interval '3 hours' );
	ELSE
		stop_time := end_time;
	END IF;

	IF ( COALESCE(end_time, now()) - begin_time ) > interval '15 hours' THEN
		cyclesize := '6 hours';
	END IF;

	WHILE cur_time < stop_time LOOP
		IF cur_time + cyclesize > stop_time THEN
			cyclesize = stop_time - cur_time;
		END IF;

		RAISE INFO 'backfilling % of reports_clean starting at %',cyclesize,cur_time;

		DELETE FROM reports_clean
		WHERE date_processed >= cur_time
			AND date_processed < ( cur_time + cyclesize );

		DELETE FROM reports_user_info
		WHERE date_processed >= cur_time
			AND date_processed < ( cur_time + cyclesize );

		PERFORM update_reports_clean( cur_time, cyclesize, false );

		cur_time := cur_time + cyclesize;
	END LOOP;

	RETURN TRUE;
END;$$;


