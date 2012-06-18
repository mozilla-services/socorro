/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

register './akela-0.1.jar'
register './socorro-analysis.jar'
register '/usr/lib/hbase/hbase-0.90.1-cdh3u0.jar'

raw = LOAD 'hbase://crash_reports' USING com.mozilla.pig.load.HBaseMultiScanLoader('$start_date', '$end_date', 'meta_data:json,processed_data:json,raw_data:dump') AS (meta_json:chararray,processed_json:chararray,raw_dump:bytearray);
gen_meta_map = FOREACH raw GENERATE com.mozilla.pig.eval.json.JsonMap(meta_json) AS meta_json_map:map[];
gen_processed_map = FOREACH raw GENERATE com.mozilla.pig.eval.json.JsonMap(processed_json) AS processed_json_map:map[];

sizes = FOREACH raw GENERATE com.mozilla.pig.eval.BytesSize(raw_dump) AS raw_size:long, com.mozilla.pig.eval.BytesSize(meta_json) AS meta_size:long, com.mozilla.pig.eval.BytesSize(processed_json) AS processed_size:long;
STORE sizes INTO '$start_date-$end_date-dumpsizes' USING PigStorage();
