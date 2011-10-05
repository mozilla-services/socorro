/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Mozilla Socorro.
 *
 * The Initial Developer of the Original Code is the Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2010
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *
 *   Xavier Stevens <xstevens@mozilla.com>, Mozilla Corporation (original author)
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

package com.mozilla.socorro.hadoop;

import static com.mozilla.socorro.hadoop.CrashReportJob.*;

import java.io.IOException;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.HashMap;
import java.util.Map;

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

public class CrashReportStats implements Tool {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(CrashReportStats.class);

	private static final String NAME = "CrashReportStats";
	private Configuration conf;

	private static final String PLUGIN = "plugin";
	private static final String KEY_DELIMITER = "\t";

	public static class CrashReportStatsMapper extends TableMapper<Text, LongWritable> {

		public enum ReportStats { JSON_PARSE_EXCEPTION, JSON_MAPPING_EXCEPTION, META_JSON_BYTES_NULL,
								  PROCESSED_JSON_BYTES_NULL, PROCESSED, PRODUCT_FILTERED, RELEASE_FILTERED,
								  TIME_FILTERED, CRASH_TIME_NULL, CRASH_TIME_PARSE_FAILED }

		private Text outputKey;
		private LongWritable one;

		private String productFilter;
		private String releaseFilter;

		private ObjectMapper jsonMapper;
		private SimpleDateFormat outputSdf;
		private long startTime;
		private long endTime;

		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Mapper#setup(org.apache.hadoop.mapreduce.Mapper.Context)
		 */
		public void setup(Context context) {
			outputKey = new Text();
			one = new LongWritable(1);

			jsonMapper = new ObjectMapper();

			Configuration conf = context.getConfiguration();

			productFilter = conf.get(PRODUCT_FILTER);
			releaseFilter = conf.get(RELEASE_FILTER);

			outputSdf = new SimpleDateFormat("yyyyMMdd");

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

				String hangId = (String)meta.get(META_JSON_HANG_ID);
				if (!StringUtils.isBlank(hangId)) {
				}

				Calendar cal = Calendar.getInstance();
				cal.setTimeInMillis(crashTime);
				StringBuilder keyPrefix = new StringBuilder();
				keyPrefix.append(outputSdf.format(cal.getTime())).append(KEY_DELIMITER);
				keyPrefix.append(product).append(KEY_DELIMITER);
				keyPrefix.append(productVersion).append(KEY_DELIMITER);

				outputKey.set(keyPrefix.toString() + "submission");
				context.write(outputKey, one);

				if (meta.containsKey(META_JSON_PROCESS_TYPE) && (PLUGIN.equalsIgnoreCase((String)meta.get(META_JSON_PROCESS_TYPE)))) {
					outputKey.set(keyPrefix.toString() + "oopp");
					context.write(outputKey, one);
				}

				byte[] processedJsonBytes = result.getValue(PROCESSED_DATA_BYTES, JSON_BYTES);
				if (processedJsonBytes != null) {
					Map<String,Object> processed = jsonMapper.readValue(new String(valueBytes), new TypeReference<Map<String,Object>>() { });

					context.getCounter(ReportStats.PROCESSED).increment(1L);

					outputKey.set(keyPrefix.toString() + "processed");
					context.write(outputKey, one);
				} else {
					context.getCounter(ReportStats.PROCESSED_JSON_BYTES_NULL).increment(1L);
				}

			} catch (JsonParseException e) {
				context.getCounter(ReportStats.JSON_PARSE_EXCEPTION).increment(1L);
			} catch (JsonMappingException e) {
				context.getCounter(ReportStats.JSON_MAPPING_EXCEPTION).increment(1L);
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
		columns.put(META_DATA_BYTES, JSON_BYTES);
		columns.put(PROCESSED_DATA_BYTES, JSON_BYTES);
		Job job = CrashReportJob.initJob(NAME, getConf(), CrashReportStats.class, CrashReportStatsMapper.class, LongSumReducer.class, LongSumReducer.class, columns, Text.class, LongWritable.class, new Path(args[0]));

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
		int res = ToolRunner.run(new Configuration(), new CrashReportStats(), args);
		System.exit(res);
	}

}
