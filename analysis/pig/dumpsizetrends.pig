register './akela-0.1.jar'                                                                                                               
register './socorro-analysis.jar'

raw = LOAD 'hbase://crash_reports' USING com.mozilla.pig.load.HBaseMultiScanLoader('$start_date', '$end_date', 'meta_data:json,processed_data:json,raw_data:dump') AS (meta_json:chararray,processed_json:chararray,raw_dump:bytearray);
gen_meta_map = FOREACH raw GENERATE com.mozilla.pig.eval.json.JsonMap(meta_json) AS meta_json_map:map[];
gen_processed_map = FOREACH raw GENERATE com.mozilla.pig.eval.json.JsonMap(processed_json) AS processed_json_map:map[];
raw_sizes = FOREACH raw GENERATE com.mozilla.pig.eval.BytesSize(raw_dump) AS size:long;
meta_sizes = FOREACH raw GENERATE com.mozilla.pig.eval.BytesSize(meta_json) AS size:long;
processed_sizes = FOREACH raw GENERATE com.mozilla.pig.eval.BytesSize(processed_json) AS size:long;
DUMP raw_sizes;
