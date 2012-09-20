/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package com.mozilla.socorro.hadoop;

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
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.util.GenericOptionsParser;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;
import org.codehaus.jackson.JsonParseException;
import org.codehaus.jackson.map.JsonMappingException;
import org.codehaus.jackson.map.ObjectMapper;
import org.codehaus.jackson.type.TypeReference;

import com.mozilla.hadoop.mapreduce.lib.UniqueIdentityReducer;
import com.mozilla.util.DateUtil;
import static com.mozilla.socorro.hadoop.CrashReportJob.*;

public class CrashReportModuleList implements Tool {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(CrashReportModuleList.class);

	private static final String NAME = "CrashReportModuleList";
	private Configuration conf;

	public static class CrashReportModuleListMapper extends TableMapper<Text, NullWritable> {

		public enum ReportStats { JSON_PARSE_EXCEPTION, JSON_MAPPING_EXCEPTION, JSON_BYTES_NULL, DATE_PARSE_EXCEPTION, BLANK_REQUIRED_FIELD }

		private Text outputKey;

		private ObjectMapper jsonMapper;

		private String productFilter;
		private String releaseFilter;
		private String osFilter;

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

			jsonMapper = new ObjectMapper();

			Configuration conf = context.getConfiguration();

			productFilter = conf.get(PRODUCT_FILTER);
			releaseFilter = conf.get(RELEASE_FILTER);
			osFilter = conf.get(OS_FILTER, "Windows NT");

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


				for (String dumpline : newlinePattern.split((String)crash.get(PROCESSED_JSON_DUMP))) {
					if (dumpline.startsWith(PROCESSED_JSON_MODULE_PATTERN)) {
						// module_str, libname, version, pdb, checksum, addrstart, addrend, unknown
						String[] dumplineSplits = pipePattern.split(dumpline);
						if (dumplineSplits.length >= 5 && !StringUtils.isBlank(dumplineSplits[3]) && !StringUtils.isBlank(dumplineSplits[4])) {
							outputKey.set(String.format("%s,%s,%s", dumplineSplits[1], dumplineSplits[3], dumplineSplits[4]));
							context.write(outputKey, NullWritable.get());
						} else {
							context.getCounter(ReportStats.BLANK_REQUIRED_FIELD).increment(1L);
						}
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
		Job job = CrashReportJob.initJob(NAME, getConf(), CrashReportModuleList.class, CrashReportModuleListMapper.class,
										 UniqueIdentityReducer.class, UniqueIdentityReducer.class, columns, Text.class,
										 NullWritable.class, new Path(args[0]));

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
		int res = ToolRunner.run(new Configuration(), new CrashReportModuleList(), args);
		System.exit(res);
	}

}
