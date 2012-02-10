\set ON_ERROR_STOP 1

DELETE FROM report_partition_info WHERE table_name = 'frames';

DROP TABLE frames CASCADE;