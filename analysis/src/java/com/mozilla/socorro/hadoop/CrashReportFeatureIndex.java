package com.mozilla.socorro.hadoop;

import static com.mozilla.socorro.hadoop.CrashReportJob.*;

import java.io.IOException;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.commons.lang.StringUtils;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.io.ImmutableBytesWritable;
import org.apache.hadoop.hbase.mapreduce.TableMapper;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.lib.reduce.LongSumReducer;
import org.apache.hadoop.util.GenericOptionsParser;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;
import org.codehaus.jackson.JsonParseException;
import org.codehaus.jackson.map.JsonMappingException;
import org.codehaus.jackson.map.ObjectMapper;
import org.codehaus.jackson.type.TypeReference;

import com.mozilla.util.DateUtil;

public class CrashReportFeatureIndex implements Tool {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(CrashReportFeatureIndex.class);
	
	private static final String NAME = "CrashReportFeatureIndex";
	private Configuration conf;
	
	// Configuration fields
	private static final String PRODUCT_FILTER = "product.filter";
	private static final String RELEASE_FILTER = "release.filter";
	private static final String OS_FILTER = "os.filter";
	private static final String CONDENSE = "condense";
	private static final String ADDONS = "addons";
	private static final String USE_CORES = "use.cores";
	private static final String USE_VERSIONS = "use.versions";
	
	private static final String MODULE_INFO_DELIMITER = "\u0002";
	
	public static class CrashReportFeatureIndexMapper extends TableMapper<Text, LongWritable> {

		public enum ReportStats { JSON_PARSE_EXCEPTION, JSON_MAPPING_EXCEPTION, JSON_BYTES_NULL, DATE_PARSE_EXCEPTION }
		
		private Text outputKey;
		private LongWritable one;
		
		private ObjectMapper jsonMapper;
		
		private String productFilter;
		private String releaseFilter;
		private String osFilter;
		private boolean condense;
		private boolean addons;
		private boolean useCores;
		private boolean useVersions;
		
		private Pattern dllPattern;
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
			one = new LongWritable(1L);
			
			jsonMapper = new ObjectMapper();
			
			Configuration conf = context.getConfiguration();
			productFilter = conf.get(PRODUCT_FILTER);
			releaseFilter = conf.get(RELEASE_FILTER);
			osFilter = conf.get(OS_FILTER, "Windows NT");
			condense = conf.getBoolean(CONDENSE, false);
			addons = conf.getBoolean(ADDONS, false);
			useCores = conf.getBoolean(USE_CORES, false);
			useVersions = conf.getBoolean(USE_VERSIONS, false);
			
			dllPattern = Pattern.compile("(\\S+)@0x[0-9a-fA-F]+$");
			newlinePattern = Pattern.compile("\n");
			pipePattern = Pattern.compile("\\|");
			
			sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
			startTime = DateUtil.getTimeAtResolution(conf.getLong(START_TIME, 0), Calendar.DATE);
			endTime = DateUtil.getEndTimeAtResolution(conf.getLong(END_TIME, System.currentTimeMillis()), Calendar.DATE);
		}

		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Mapper#map(KEYIN, VALUEIN, org.apache.hadoop.mapreduce.Mapper.Context)
		 */
		@SuppressWarnings("unchecked")
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
						return;
					}
				} 
				if (!StringUtils.isBlank(releaseFilter)) {
					if (crash.containsKey(PROCESSED_JSON_VERSION) && !crash.get(PROCESSED_JSON_VERSION).equals(releaseFilter)) {
						return;
					}
				}
				
				String osName = (String)crash.get(PROCESSED_JSON_OS_NAME);
				if (!StringUtils.isBlank(osFilter)) {
					if (osName == null || !osName.equals(osFilter)) {
						return;
					}
				}
				
				// Set the value to the date
				String dateProcessed = (String)crash.get(PROCESSED_JSON_DATE_PROCESSED);
				long crashTime = sdf.parse(dateProcessed).getTime();
				// Filter if the processed date is not within our window
				if (crashTime < startTime || crashTime > endTime) {
					return;
				}
				
				String signame = (String)crash.get(PROCESSED_JSON_SIGNATURE);
				if (!StringUtils.isBlank(signame)) {
					if (condense) {
						Matcher sigMatcher = dllPattern.matcher(signame);
						if (sigMatcher.find() && sigMatcher.groupCount() > 0) {
							signame = sigMatcher.group(1);
						}
					}
					
					signame = signame + "|" + crash.get(PROCESSED_JSON_REASON);
				} else {
					signame = "(no signature)";
				}
				
				if (addons) {
					List<Object> addons = (ArrayList<Object>)crash.get(ADDONS);
					if (addons != null) {
						for (Object addon : addons) {
							List<String> addonList = (ArrayList<String>)addon;
							String addonName = addonList.get(0);
							String version = addonList.get(1);

							if (useVersions) {
								outputKey.set(addonName + MODULE_INFO_DELIMITER + version);
							} else {
								outputKey.set(addonName);
							}
							context.write(outputKey, one);
						}
					}
				}
				
				for (String dumpline : newlinePattern.split((String)crash.get(PROCESSED_JSON_DUMP))) {
					if (dumpline.startsWith(PROCESSED_JSON_CPU_PATTERN)) {
						if (useCores) {
							String[] dumplineSplits = pipePattern.split(dumpline);
							String arch = String.format("%s with %s cores", new Object[] { dumplineSplits[1], dumplineSplits[3] });
							outputKey.set(arch);
							context.write(outputKey, one);
						}
					} else if (dumpline.startsWith(PROCESSED_JSON_MODULE_PATTERN)) {
						// module_str, libname, version, pdb, checksum, addrstart, addrend, unknown
						String[] dumplineSplits = pipePattern.split(dumpline);
						
						String moduleName;
						String version;
						if (osName.startsWith("Win")) {
							// we only have good version data on windows
							moduleName = dumplineSplits[1];
							version = dumplineSplits[2];
						} else {
							moduleName = dumplineSplits[1];
							version = dumplineSplits[4];
						}

						if (useVersions) {
							outputKey.set(moduleName + MODULE_INFO_DELIMITER + version);
						} else {
							outputKey.set(moduleName);
						}
						
						context.write(outputKey, one);
					}
				}
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
		Job job = CrashReportJob.initJob(NAME, getConf(), CrashReportFeatureIndex.class, CrashReportFeatureIndexMapper.class, LongSumReducer.class, LongSumReducer.class, columns, Text.class, LongWritable.class, new Path(args[0]));
		
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
		System.out.println(CONDENSE + "<true|false>");
		System.out.println(ADDONS + "=<true|false>");
		System.out.println(USE_VERSIONS + "=<true|false>");
		System.out.println(USE_CORES + "=<true|false>");
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
		int res = ToolRunner.run(new Configuration(), new CrashReportFeatureIndex(), args);
		System.exit(res);
	}
	
}
