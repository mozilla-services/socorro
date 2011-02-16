package com.mozilla.socorro.hadoop;

import static com.mozilla.socorro.hadoop.CrashReportJob.*;

import java.io.IOException;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Pattern;

import org.apache.commons.lang.StringUtils;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.io.ImmutableBytesWritable;
import org.apache.hadoop.hbase.mapreduce.TableMapper;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.lib.reduce.IntSumReducer;
import org.apache.hadoop.util.GenericOptionsParser;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;
import org.codehaus.jackson.JsonParseException;
import org.codehaus.jackson.map.JsonMappingException;
import org.codehaus.jackson.map.ObjectMapper;
import org.codehaus.jackson.type.TypeReference;

import com.mozilla.util.DateUtil;

public class HardwareAccel implements Tool {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(HardwareAccel.class);
	
	private static final String NAME = "HardwareAccel";
	private Configuration conf;
	
	public static class HardwareAccelMapper extends TableMapper<Text, IntWritable> {

		public enum ReportStats { JSON_PARSE_EXCEPTION, JSON_MAPPING_EXCEPTION, JSON_BYTES_NULL, DATE_PARSE_EXCEPTION, PRODUCT_FILTERED, RELEASE_FILTERED, OS_FILTERED, OS_VERSION_FILTERED, TIME_FILTERED }
		
		private Text outputKey;
		private IntWritable one;
		
		private ObjectMapper jsonMapper;
		
		private String productFilter;
		private String releaseFilter;
		private String osFilter;
		private String osVersionFilter;
		
		private Pattern newlinePattern;
		private Pattern pipePattern;

		private SimpleDateFormat sdf;
		private long startTime;
		private long endTime;
		
		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Mapper#setup(org.apache.hadoop.mapreduce.Mapper.Context)
		 */
		public void setup(Context context) {
			outputKey = new Text();
			one = new IntWritable(1);
			
			jsonMapper = new ObjectMapper();
			
			Configuration conf = context.getConfiguration();
			
			productFilter = conf.get(PRODUCT_FILTER);
			releaseFilter = conf.get(RELEASE_FILTER);
			osFilter = conf.get(OS_FILTER, "Windows NT");
			osVersionFilter = conf.get(OS_VERSION_FILTER, "6.1.7600");
			newlinePattern = Pattern.compile("\n");
			pipePattern = Pattern.compile("\\|");
			
			sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
			startTime = DateUtil.getTimeAtResolution(conf.getLong(START_TIME, 0), Calendar.DATE);
			endTime = DateUtil.getEndTimeAtResolution(conf.getLong(END_TIME, System.currentTimeMillis()), Calendar.DATE);
		}

		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Mapper#map(KEYIN, VALUEIN, org.apache.hadoop.mapreduce.Mapper.Context)
		 */
		public void map(ImmutableBytesWritable key, Result result, Context context) throws InterruptedException, IOException {
			try {
				byte[] valueBytes = result.getValue(PROCESSED_DATA_BYTES, JSON_BYTES);
				if (valueBytes == null) {
					context.getCounter(ReportStats.JSON_BYTES_NULL).increment(1L);
					return;
				}
				String value = new String(valueBytes);
				// This is an untyped parse so the caller is expected to know the types
				Map<String,Object> crash = jsonMapper.readValue(value, new TypeReference<Map<String,Object>>() { });
				
				// Filter row if filter(s) are set and it doesn't match
				if (!StringUtils.isBlank(productFilter)) {
					if (crash.containsKey(PROCESSED_JSON_PRODUCT) && !crash.get(PROCESSED_JSON_PRODUCT).equals(productFilter)) {
						context.getCounter(ReportStats.PRODUCT_FILTERED).increment(1L);
						return;
					}
				} 
				if (!StringUtils.isBlank(releaseFilter)) {
					if (crash.containsKey(PROCESSED_JSON_VERSION) && !crash.get(PROCESSED_JSON_VERSION).equals(releaseFilter)) {
						context.getCounter(ReportStats.RELEASE_FILTERED).increment(1L);
						return;
					}
				}
				
				String osName = (String)crash.get(PROCESSED_JSON_OS_NAME);
				if (!StringUtils.isBlank(osFilter)) {
					if (osName == null || !osName.equals(osFilter)) {
						context.getCounter(ReportStats.OS_FILTERED).increment(1L);
						return;
					}
				}
				
				String osVersion = (String)crash.get(PROCESSED_JSON_OS_VERSION);
				if (!StringUtils.isBlank(osVersionFilter)) {
					if (osVersion == null || !osVersion.startsWith(osVersionFilter)) {
						context.getCounter(ReportStats.OS_VERSION_FILTERED).increment(1L);
						return;
					}
				}
				
				// Set the value to the date
				String dateProcessed = (String)crash.get(PROCESSED_JSON_DATE_PROCESSED);
				long crashTime = sdf.parse(dateProcessed).getTime();
				// Filter if the processed date is not within our window
				if (crashTime < startTime || crashTime > endTime) {
					context.getCounter(ReportStats.TIME_FILTERED).increment(1L);
					return;
				}
				
				boolean hadModuleLoaded = false;
				for (String dumpline : newlinePattern.split((String)crash.get(PROCESSED_JSON_DUMP))) {
					if (dumpline.startsWith(PROCESSED_JSON_MODULE_PATTERN)) {
						// module_str, libname, version, pdb, checksum, addrstart, addrend, unknown
						String[] dumplineSplits = pipePattern.split(dumpline);
						if (!StringUtils.isBlank(dumplineSplits[1]) && dumplineSplits[1].startsWith("d2d")) {
							hadModuleLoaded = true;
							outputKey.set(dumplineSplits[1]);
							break;
						}
					}
				}
				
				if (!hadModuleLoaded) {
					outputKey.set("no_module");
				}
				context.write(outputKey, one);
			} catch (JsonParseException e) {
				context.getCounter(ReportStats.JSON_PARSE_EXCEPTION).increment(1L);
			} catch (JsonMappingException e) {
				context.getCounter(ReportStats.JSON_MAPPING_EXCEPTION).increment(1L);
			} catch (ParseException e) {
				context.getCounter(ReportStats.DATE_PARSE_EXCEPTION).increment(1L);
			}
		}
		
	}
	
	/**
	 * @param args
	 * @return
	 * @throws IOException
	 * @throws ParseException 
	 */
	public Job initJob(String[] args) throws IOException, ParseException {
		Map<byte[], byte[]> columns = new HashMap<byte[], byte[]>();
		columns.put(PROCESSED_DATA_BYTES, JSON_BYTES);
		Job job = CrashReportJob.initJob(NAME, getConf(), HardwareAccel.class, HardwareAccelMapper.class, IntSumReducer.class, IntSumReducer.class, columns, Text.class, IntWritable.class, new Path(args[0]));
		job.setNumReduceTasks(1);
		
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
		System.out.println(OS_FILTER + "=<os-name>");
		System.out.println(OS_VERSION_FILTER + "=<os-version>");
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
		int res = ToolRunner.run(new Configuration(), new HardwareAccel(), args);
		System.exit(res);
	}

}
