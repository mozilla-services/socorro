\SET ON_ERROR_STOP 1

BEGIN;

-- function

CREATE OR REPLACE FUNCTION update_adu (
	updateday date )
RETURNS BOOLEAN
LANGUAGE plpgsql 
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
BEGIN
-- daily batch update procedure to update the 
-- adu-product matview, used to power graphs
-- gets its data from raw_adu, which is populated
-- daily by metrics

-- check if raw_adu has been updated.  otherwise, abort.
PERFORM 1 FROM raw_adu 
WHERE "date" = updateday
LIMIT 1;

IF NOT FOUND THEN
	RAISE EXCEPTION 'raw_adu not updated for %',updateday;
END IF;

-- check if ADU has already been run for the date

PERFORM 1 FROM product_adu
WHERE adu_date = updateday LIMIT 1;

IF FOUND THEN
	RAISE EXCEPTION 'update_adu has already been run for %', updateday;
END IF;

INSERT INTO product_adu ( product_version_id,
		adu_date, adu_count )
SELECT product_version_id,
	updateday,
	coalesce(sum(raw_adu.adu_count), 0)
FROM product_versions
	LEFT OUTER JOIN raw_adu
		ON product_versions.product_name = raw_adu.product_name
		AND product_versions.version_string = raw_adu.product_version
		AND raw_adu.date = updateday
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
GROUP BY product_version_id;

RETURN TRUE;
END; $f$;

-- backfill adu

DO $f$
DECLARE aduday DATE;
BEGIN
FOR aduday IN SELECT i 
	FROM generate_series(timestamp '2011-07-24', timestamp '2011-07-26', '1 day') as gs(i)
	LOOP
	
	PERFORM update_adu(aduday);
	
END LOOP;
END;$f$;
	





	