\set ON_ERROR_STOP 1

BEGIN;

DROP TABLE IF EXISTS last_tcbsig;
DROP TABLE IF EXISTS last_tcburl;
DROP TABLE IF EXISTS last_urlsig;
DROP TABLE IF EXISTS priorityjobs_log_sjc_backup;
DROP TABLE IF EXISTS sequence_numbers;
DROP TABLE IF EXISTS drop_fks;

END;


