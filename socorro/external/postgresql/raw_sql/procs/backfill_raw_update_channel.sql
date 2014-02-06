CREATE OR REPLACE FUNCTION backfill_raw_update_channel(
    begin_time timestamp with time zone,
    end_time timestamp with time zone DEFAULT NULL::timestamp with time zone
)
    RETURNS boolean
    LANGUAGE plpgsql
AS $_$
-- administrative utility for backfilling raw_update_channel to the selected date
-- intended to be called on the command line
-- uses a larger cycle (6 hours) if we have to backfill several days of data
-- note that this takes timestamptz as parameters

DECLARE cyclesize INTERVAL := '1 hour';
	stop_time timestamptz;
	cur_time timestamptz := begin_time;
BEGIN
	IF end_time IS NULL OR end_time > (now() - interval '3 hours') THEN
	-- if no end time supplied, then default to three hours ago
	-- on the hour
		stop_time := (date_trunc('hour', now()) - interval '3 hours');
	ELSE
		stop_time := end_time;
	END IF;

	IF (COALESCE(end_time, now()) - begin_time) > interval '15 hours' THEN
		cyclesize := '6 hours';
	END IF;

	WHILE cur_time < stop_time LOOP
		IF cur_time + cyclesize > stop_time THEN
			cyclesize = stop_time - cur_time;
		END IF;

		RAISE INFO 'backfilling % of raw_update_channel starting at %', cyclesize, cur_time;
		PERFORM update_raw_update_channel(cur_time, cyclesize, false);
		cur_time := cur_time + cyclesize;
	END LOOP;

	RETURN TRUE;

END;
$_$;
