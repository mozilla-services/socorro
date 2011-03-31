register './akela-0.1.jar'                                                                                                               
register './socorro-analysis.jar'
/* Not sure why we have to register this JAR when it's already in Pig's classpath but we do */
register '/usr/lib/hbase/hbase-0.90.1-CDH3B4.jar'

raw = LOAD 'hbase://crash_reports' USING com.mozilla.pig.load.HBaseMultiScanLoader('20110216', '20110216', 'processed_data:json') AS (k:chararray, processed_json:chararray);
genmap = FOREACH raw GENERATE k,com.mozilla.pig.eval.json.JsonMap(processed_json) AS processed_json_map:map[];
product_filtered = FILTER genmap BY processed_json_map#'product' == 'Firefox' AND processed_json_map#'os_name' == 'Windows NT';
stack_bag = FOREACH product_filtered GENERATE k,com.mozilla.socorro.pig.eval.FrameBag(processed_json_map#'dump') AS frames:bag{frame:tuple(f1:chararray, f2:chararray, f3:chararray, f4:chararray, f5:chararray, f6:chararray, f7:chararray)};
flat_stack = FOREACH stack_bag GENERATE k,FLATTEN(frames);
STORE flat_stack INTO '$start_date-$end_date-stackframes' USING PigStorage();

method_sigs = FOREACH flat_stack GENERATE $5 AS (method_sig:chararray);
grouped_sigs = GROUP method_sigs BY method_sig;
distinct_sigs = FOREACH grouped_sigs GENERATE group, COUNT(method_sigs.method_sig);
STORE distinct_sigs INTO '$start_date-$end_date-method-signatures' USING PigStorage();