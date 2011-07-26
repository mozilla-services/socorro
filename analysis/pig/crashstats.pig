register './akela-0.1.jar'                                                                                                               
register './socorro-analysis.jar'
register '/usr/lib/hbase/hbase-0.90.1-cdh3u0.jar'

raw = LOAD 'hbase://crash_reports' USING com.mozilla.pig.load.HBaseMultiScanLoader('$start_date', '$end_date', 'meta_data:json,processed_data:json,raw_data:dump') AS (meta_json:chararray,processed_json:chararray,raw_dump:bytearray);
gen_meta_map = FOREACH raw GENERATE com.mozilla.pig.eval.json.JsonMap(meta_json) AS meta_json_map:map[];
product_filtered = FILTER gen_meta_map BY meta_json_map#'ProductName' == 'Firefox';

/* in seconds need to compare to start_date and stop_date */
start_date_millis = com.mozilla.pig.eval.date.ParseDate('yyyyMMdd', $start_date);
end_date_millis = com.mozilla.pig.eval.date.ParseDate('yyyyMMdd', $end_date);
time_filtered = FILTER product_filtered BY ((meta_json_map#'CrashTime' * 1000) >= start_date_millis AND (meta_json_map#'CrashTime' * 1000) <= end_date_millis);

/* count and output submission */
submissions = FOREACH time_filtered GENERATE (com.mozilla.pig.eval.date.FormatDate('yyyyMMdd', (meta_json_map#'CrashTime'*1000)), meta_json_map#'ProductName', meta_json_map#'Version', 'submissions');
STORE submissions INTO '$start_date-$end_date-submissions' USING PigStorage();

/* count and output hang */
hang_filtered = FILTER time_filtered BY meta_json_map#'HangId' is not null;
gen_hangs = FOREACH hang_filtered GENERATE (com.mozilla.pig.eval.date.FormatDate('yyyyMMdd', (meta_json_map#'CrashTime'*1000)), meta_json_map#'ProductName', meta_json_map#'Version', 'hangs');
STORE gen_hangs INTO '$start_date-$end_date-hangs' USING PigStorage();

/* count and output oopp */
oopp_filtered = FILTER time_filtered BY meta_json_map#'ProcessType' is not null AND meta_json_map#'ProcessType' == 'plugin';
gen_oopp = FOREACH oopp_filtered GENERATE (com.mozilla.pig.eval.date.FormatDate('yyyyMMdd', (meta_json_map#'CrashTime'*1000)), meta_json_map#'ProductName', meta_json_map#'Version', 'oopp');
STORE gen_oopp INTO '$start_date-$end_date-oopps' USING PigStorage();

/* count and output processed */
gen_processed_map = FOREACH oopp_filtered GENERATE com.mozilla.hadoop.pig.eval.json.JsonMap(processed_json) AS processed_json_map:map[];
processed_filtered = FILTER gen_processed_map BY processed_json_map is not null;

STORE processed_filtered INTO '$start_date-$end_date-processed' USING PigStorage();