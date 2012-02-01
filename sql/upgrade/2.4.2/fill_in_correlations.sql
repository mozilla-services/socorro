\set ON_ERROR_STOP 1

SELECT backfill_correlations(CURRENT_DATE - 1);
