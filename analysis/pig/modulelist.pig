register './akela-0.1.jar'                                                                                                               
register './socorro-analysis.jar'
/* Not sure why we have to register this JAR when it's already in Pig's classpath but we do */
register '/usr/lib/hbase/hbase-0.90.1-cdh3u0.jar'

raw = LOAD 'hbase://crash_reports' USING com.mozilla.pig.load.HBaseMultiScanLoader('$start_date', '$end_date', 'processed_data:json') AS (k:chararray, processed_json:chararray);
genmap = FOREACH raw GENERATE com.mozilla.pig.eval.json.JsonMap(processed_json) AS processed_json_map:map[];
product_filtered = FILTER genmap BY processed_json_map#'product' == 'Firefox' AND processed_json_map#'os_name' == 'Windows NT';
module_bag = FOREACH product_filtered GENERATE com.mozilla.socorro.pig.eval.ModuleBag(processed_json_map#'dump') AS modules:bag{module_tuple:tuple(f1:chararray, f2:chararray, f3:chararray, f4:chararray, f5:chararray, f6:chararray, f7:chararray, f8:chararray)};
filtered_modules = FILTER module_bag BY modules is not null AND modules.f1 is not null AND modules.f3 is not null AND modules.f4 is not null;
flat_modules = FOREACH filtered_modules GENERATE FLATTEN(modules);
modules_list = FOREACH flat_modules GENERATE f1, f3, f4;
STORE modules_list INTO '$start_date-$end_date-module-list' USING PigStorage(',');
