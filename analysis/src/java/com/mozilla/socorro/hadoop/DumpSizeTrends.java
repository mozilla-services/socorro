package com.mozilla.socorro.hadoop;

import static com.mozilla.socorro.hadoop.CrashReportJob.*;

import java.io.IOException;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.commons.lang.StringUtils;
import org.apache.commons.math.stat.descriptive.DescriptiveStatistics;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.io.ImmutableBytesWritable;
import org.apache.hadoop.hbase.mapreduce.TableMapper;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.util.GenericOptionsParser;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;
import org.codehaus.jackson.JsonParseException;
import org.codehaus.jackson.map.JsonMappingException;
import org.codehaus.jackson.map.ObjectMapper;
import org.codehaus.jackson.type.TypeReference;

import com.mozilla.util.DateUtil;

public class DumpSizeTrends implements Tool {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(DumpSizeTrends.class);
	
	private static final String NAME = "DumpSizeTrends";
	private Configuration conf;
	
	private static final String KEY_DELIMITER = "\u0001";
	private static final String TAB_DELIMITER = "\t";
	
	public static class DumpSizeTrendsMapper extends TableMapper<Text, IntWritable> {

		public enum ReportStats { RAW_BYTES_NULL, PROCESSED_BYTES_NULL, JSON_PARSE_EXCEPTION, JSON_MAPPING_EXCEPTION, 
								  META_JSON_BYTES_NULL, PROCESSED_JSON_BYTES_NULL, PROCESSED, PRODUCT_FILTERED, 
								  RELEASE_FILTERED, TIME_FILTERED, CRASH_TIME_NULL, CRASH_TIME_PARSE_FAILED, OOM_ERROR }
		
		private Text outputKey;
		private IntWritable outputValue;
		
		private ObjectMapper jsonMapper;
		private SimpleDateFormat outputSdf;
		
		private String productFilter;
		private String releaseFilter;
		private long startTime;
		private long endTime;
		
		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Mapper#setup(org.apache.hadoop.mapreduce.Mapper.Context)
		 */
		public void setup(Context context) {
			outputKey = new Text();
			outputValue = new IntWritable();
			
			jsonMapper = new ObjectMapper();
			
			outputSdf = new SimpleDateFormat("yyyyMMdd");
			
			Configuration conf = context.getConfiguration();
			productFilter = conf.get(PRODUCT_FILTER);
			releaseFilter = conf.get(RELEASE_FILTER);
			
			startTime = DateUtil.getTimeAtResolution(conf.getLong(START_TIME, 0), Calendar.DATE);
			endTime = DateUtil.getEndTimeAtResolution(conf.getLong(END_TIME, System.currentTimeMillis()), Calendar.DATE);
		}

		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Mapper#map(KEYIN, VALUEIN, org.apache.hadoop.mapreduce.Mapper.Context)
		 */
		public void map(ImmutableBytesWritable key, Result result, Context context) throws InterruptedException, IOException {
			try {
				byte[] valueBytes = result.getValue(META_DATA_BYTES, JSON_BYTES);
				if (valueBytes == null) {
					context.getCounter(ReportStats.META_JSON_BYTES_NULL).increment(1L);
					return;
				}
				
				// This is an untyped parse so the caller is expected to know the types
				Map<String,Object> meta = jsonMapper.readValue(new String(valueBytes), new TypeReference<Map<String,Object>>() { });
				
				String product = null;
				String productVersion = null;
				if (meta.containsKey(META_JSON_PRODUCT_NAME)) {
					product = (String)meta.get(META_JSON_PRODUCT_NAME);
				}
				if (meta.containsKey(META_JSON_PRODUCT_VERSION)) {
					productVersion = (String)meta.get(META_JSON_PRODUCT_VERSION);
				}
				
				// Filter row if filter(s) are set and it doesn't match
				if (!StringUtils.isBlank(productFilter)) {
					if (product == null || !product.equals(productFilter)) {
						context.getCounter(ReportStats.PRODUCT_FILTERED).increment(1L);
						return;
					}
				} 
				if (!StringUtils.isBlank(releaseFilter)) {
					if (productVersion == null || !productVersion.equals(releaseFilter)) {
						context.getCounter(ReportStats.RELEASE_FILTERED).increment(1L);
						return;
					}
				}
				
				String crashTimeStr = (String)meta.get(META_JSON_CRASH_TIME);
				if (!meta.containsKey(META_JSON_CRASH_TIME)) {
					context.getCounter(ReportStats.CRASH_TIME_NULL).increment(1L);
				}
				
				long crashTime = 0L;
				try {
					crashTime = Long.parseLong(crashTimeStr) * 1000L;
				} catch (NumberFormatException e) {
					context.getCounter(ReportStats.CRASH_TIME_PARSE_FAILED).increment(1L);
					return;
				}
				// Filter if the crash time is not within our window
				if (crashTime < startTime || crashTime > endTime) {
					context.getCounter(ReportStats.TIME_FILTERED).increment(1L);
					return;
				}
								
				Calendar cal = Calendar.getInstance();
				cal.setTimeInMillis(crashTime);
				StringBuilder keyPrefix = new StringBuilder();
				keyPrefix.append(outputSdf.format(cal.getTime())).append(KEY_DELIMITER);
				keyPrefix.append(product).append(KEY_DELIMITER);
				keyPrefix.append(productVersion).append(KEY_DELIMITER);
				
				valueBytes = result.getValue(RAW_DATA_BYTES, DUMP_BYTES);
				if (valueBytes == null) {
					context.getCounter(ReportStats.RAW_BYTES_NULL).increment(1L);
				} else {
					outputKey.set(keyPrefix.toString() + "raw");
					outputValue.set(valueBytes.length);
					context.write(outputKey, outputValue);
				}
				
				valueBytes = result.getValue(PROCESSED_DATA_BYTES, JSON_BYTES);
				if (valueBytes != null) {
					outputKey.set(keyPrefix.toString() + "processed");
					outputValue.set(valueBytes.length);
					context.write(outputKey, outputValue);
				} else {
					context.getCounter(ReportStats.PROCESSED_JSON_BYTES_NULL).increment(1L);
				}
				
			} catch (JsonParseException e) {
				context.getCounter(ReportStats.JSON_PARSE_EXCEPTION).increment(1L);
			} catch (JsonMappingException e) {
				context.getCounter(ReportStats.JSON_MAPPING_EXCEPTION).increment(1L);
			} catch (OutOfMemoryError e) {
				System.out.println("OutOfMemoryError on row: " + new String(result.getRow()));
				context.getCounter(ReportStats.OOM_ERROR).increment(1L);
			}
		}
		
	}	

	public static class DumpSizeTrendsReducer extends Reducer<Text, IntWritable, Text, Text> {
				
		private Text outputKey = null;
		private Text outputValue = null;
		private Pattern keyPattern = null;
		
		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Reducer#setup(org.apache.hadoop.mapreduce.Reducer.Context)
		 */
		public void setup(Context context) {
			keyPattern = Pattern.compile(KEY_DELIMITER);
			outputKey = new Text();
			outputValue = new Text();
		}
		
		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Reducer#cleanup(org.apache.hadoop.mapreduce.Reducer.Context)
		 */
		public void cleanup(Context context) {
		}
		
		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Reducer#reduce(KEYIN, java.lang.Iterable, org.apache.hadoop.mapreduce.Reducer.Context)
		 */
		public void reduce(Text key, Iterable<IntWritable> values, Context context) throws IOException,InterruptedException {
			Iterator<IntWritable> iter = values.iterator();
			DescriptiveStatistics stats = new DescriptiveStatistics();
			long sum = 0L;
			while (iter.hasNext()) {
				long curValue = iter.next().get();
				stats.addValue(curValue);
				sum += curValue;
			}
			
			Matcher m = keyPattern.matcher(key.toString());
			if (m.find()) {
				outputKey.set(m.replaceAll(TAB_DELIMITER));
			} else {
				outputKey.set(key.toString());
			}
			
			// Output the median along with total size
			StringBuilder sb = new StringBuilder();
			sb.append(stats.getN()).append(TAB_DELIMITER);
			sb.append(stats.getPercentile(50.0d)).append(TAB_DELIMITER);
			sb.append(sum);
			outputValue.set(sb.toString());
			context.write(outputKey, outputValue);
		}
		
	}
	
	/**
	 * @param args
	 * @return
	 * @throws IOException
	 * @throws ParseException 
	 */
	public Job initJob(String[] args) throws IOException, ParseException {
		conf.set("mapred.child.java.opts", "-Xmx1024m");
		conf.setBoolean("mapred.map.tasks.speculative.execution", false);
		
		Map<byte[], byte[]> columns = new HashMap<byte[], byte[]>();
		columns.put(RAW_DATA_BYTES, DUMP_BYTES);
		columns.put(META_DATA_BYTES, JSON_BYTES);
		columns.put(PROCESSED_DATA_BYTES, JSON_BYTES);
		Job job = CrashReportJob.initJob(NAME, getConf(), DumpSizeTrends.class, DumpSizeTrendsMapper.class, null, DumpSizeTrendsReducer.class, columns, Text.class, Text.class, new Path(args[0]));
		job.setMapOutputKeyClass(Text.class);
		job.setMapOutputValueClass(IntWritable.class);
		
		return job;
	}

	/**
	 * @return
	 */
	private static int printUsage() {
		System.out.println("Usage: " + NAME + " [generic-options] <output-path>");
		System.out.println();
		System.out.println("Configurable Properties:");
		System.out.println(PRODUCT_FILTER + "=<product-name>");
		System.out.println(RELEASE_FILTER + "=<release-version>");
		System.out.println(START_DATE + "=<yyyyMMdd>");
		System.out.println(END_DATE + "=<yyyyMMdd>");
		System.out.println();
		GenericOptionsParser.printGenericCommandUsage(System.out);
		return -1;
	}
	
	/* (non-Javadoc)
	 * @see org.apache.hadoop.util.Tool#run(java.lang.String[])
	 */
	public int run(String[] args) throws Exception {
		if (args.length != 1) {
			return printUsage();
		}
		
		int rc = -1;
		Job job = initJob(args);
		job.waitForCompletion(true);
		if (job.isSuccessful()) {
			rc = 0;
		}
		
		return rc;
	}

	/* (non-Javadoc)
	 * @see org.apache.hadoop.conf.Configurable#getConf()
	 */
	public Configuration getConf() {
		return this.conf;
	}

	/* (non-Javadoc)
	 * @see org.apache.hadoop.conf.Configurable#setConf(org.apache.hadoop.conf.Configuration)
	 */
	public void setConf(Configuration conf) {
		this.conf = conf;
	}
	
	/**
	 * @param args
	 * @throws Exception
	 */
	public static void main(String[] args) throws Exception {
		int res = ToolRunner.run(new Configuration(), new DumpSizeTrends(), args);
		System.exit(res);
	}
}
