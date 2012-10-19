\set ON_ERROR_STOP 1

BEGIN;

DROP FUNCTION IF EXISTS backfill_adu ( date );

CREATE OR REPLACE FUNCTION public.backfill_adu(updateday date)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
BEGIN
-- stored procudure to delete and replace one day of
-- product_adu, optionally only for a specific product
-- intended to be called by backfill_matviews

DELETE FROM product_adu
WHERE adu_date = updateday;

PERFORM update_adu(updateday, false);

RETURN TRUE;
END; $function$

COMMIT;
