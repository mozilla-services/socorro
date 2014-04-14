CREATE OR REPLACE FUNCTION backfill_correlations(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

PERFORM update_correlations_addon(updateday, false);
PERFORM update_correlations_core(updateday, false);
PERFORM update_correlations_module(updateday, false);

RETURN TRUE;
END; $$;


