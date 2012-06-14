\set ON_ERROR_STOP 1

DROP VIEW IF EXISTS jobs_in_queue;

DROP VIEW IF EXISTS processor_count;

CREATE OR REPLACE VIEW current_server_status AS 
SELECT 
	date_recently_completed,
 	date_oldest_job_queued,
 	extract('epoch' from (date_created - date_oldest_job_queued)) as oldest_job_age,
 	avg_process_sec,
 	avg_wait_sec,
 	waiting_job_count,
 	processors_count,
 	date_created
FROM server_status
ORDER BY date_created DESC LIMIT 1;

ALTER VIEW current_server_status OWNER TO breakpad_rw;

GRANT SELECT on current_server_status TO monitoring;
 

