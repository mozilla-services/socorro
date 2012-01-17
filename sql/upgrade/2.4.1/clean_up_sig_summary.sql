\set ON_ERROR_STOP 1

DROP TABLE IF EXISTS os_signature_counts;

DROP TABLE IF EXISTS product_signature_counts;

DROP TABLE IF EXISTS uptime_signature_counts;

DROP FUNCTION IF EXISTS update_os_signature_counts ( date, boolean );

DROP FUNCTION IF EXISTS backfill_os_signature_counts ( date );

DROP FUNCTION IF EXISTS update_product_signature_counts ( date, boolean );

DROP FUNCTION IF EXISTS backfill_product_signature_counts ( date );

DROP FUNCTION IF EXISTS update_uptime_signature_counts ( date, boolean );

DROP FUNCTION IF EXISTS backfill_uptime_signature_counts ( date );