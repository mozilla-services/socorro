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

import java.io.IOException;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
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
import org.apache.hadoop.util.GenericOptionsParser;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;
import org.codehaus.jackson.JsonParseException;
import org.codehaus.jackson.map.JsonMappingException;
import org.codehaus.jackson.map.ObjectMapper;
import org.codehaus.jackson.type.TypeReference;

import com.mozilla.socorro.dao.CrashCountDao;
import com.mozilla.socorro.dao.hbase.HbaseCrashCountDao;
import com.mozilla.util.DateUtil;
import static com.mozilla.socorro.hadoop.CrashReportJob.*;

/**
 * CrashCount will read crash report data in from HBase and count
 * the number of crashes at different levels (product, version, OS, signature, module,
 * module_version, addon, addon_version).
 *
 */
public class CrashCount implements Tool {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(CrashCount.class);

	private static final String NAME = "CrashCount";
	private Configuration conf;

	public static class CrashCountMapper extends TableMapper<Text, LongWritable> {

		public enum ReportStats { JSON_PARSE_EXCEPTION, JSON_MAPPING_EXCEPTION, JSON_BYTES_NULL, DATE_PARSE_EXCEPTION, PROCESSED }

		private CrashCountDao ccDao;
		private ObjectMapper jsonMapper;
		private Pattern newlinePattern;
		private Pattern pipePattern;
		private SimpleDateFormat sdf;
		private SimpleDateFormat rowSdf;
		private long startTime;
		private long endTime;

		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Mapper#setup(org.apache.hadoop.mapreduce.Mapper.Context)
		 */
		public void setup(Context context) {

			try {
				ccDao = new HbaseCrashCountDao();
			} catch (IOException e) {
				throw new RuntimeException("Error creating Crash Count DAO", e);
			}

			jsonMapper = new ObjectMapper();

			Configuration conf = context.getConfiguration();

			newlinePattern = Pattern.compile("\n");
			pipePattern = Pattern.compile("\\|");

			sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
			rowSdf = new SimpleDateFormat("yyyyMMdd");

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

				String product = null;
				String productVersion = null;
				if (crash.containsKey(PROCESSED_JSON_PRODUCT)) {
					product = (String)crash.get(PROCESSED_JSON_PRODUCT);
				}
				if (crash.containsKey(PROCESSED_JSON_VERSION)) {
					productVersion = (String)crash.get(PROCESSED_JSON_VERSION);
				}

				// Set the value to the date
				String dateProcessed = (String)crash.get(PROCESSED_JSON_DATE_PROCESSED);
				long crashTime = sdf.parse(dateProcessed).getTime();
				// Filter if the processed date is not within our window
				if (crashTime < startTime || crashTime > endTime) {
					return;
				}

				String osName = (String)crash.get(PROCESSED_JSON_OS_NAME);
				if (osName == null) {
					return;
				}

				String signame = (String)crash.get(PROCESSED_JSON_SIGNATURE);
				if (signame != null) {
					signame = signame + "|" + crash.get(PROCESSED_JSON_REASON);
				} else {
					signame = "(no signature)";
				}

				String arch = null;
				Map<String, String> moduleVersions = new HashMap<String,String>();
				for (String dumpline : newlinePattern.split((String)crash.get(PROCESSED_JSON_DUMP))) {
					if (dumpline.startsWith(PROCESSED_JSON_CPU_PATTERN)) {
						String[] dumplineSplits = pipePattern.split(dumpline);
						arch = String.format("%s with %s cores", new Object[] { dumplineSplits[1], dumplineSplits[3] });
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

						moduleVersions.put(moduleName, version);
					}
				}

				Map<String, String> addonVersions = new HashMap<String,String>();
				List<Object> addons = (ArrayList<Object>)crash.get(PROCESSED_JSON_ADDONS);
				if (addons != null) {
					for (Object addon : addons) {
						List<String> addonList = (ArrayList<String>)addon;
						String addonName = addonList.get(0);
						String version = addonList.get(1);

						addonVersions.put(addonName, version);
					}
				}

				if (!StringUtils.isBlank(product) && !StringUtils.isBlank(productVersion) &&
					!StringUtils.isBlank(osName) && !StringUtils.isBlank(signame)) {
					Calendar cal = Calendar.getInstance();
					cal.setTimeInMillis(DateUtil.getTimeAtResolution(crashTime, Calendar.DATE));
					ccDao.incrementCounts(rowSdf.format(cal.getTime()), product, productVersion, osName, signame, arch, moduleVersions, addonVersions);
				}
				context.getCounter(ReportStats.PROCESSED).increment(1L);
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
		Job job = CrashReportJob.initJob(NAME, getConf(), CrashCount.class, CrashCountMapper.class, null, null, columns, Text.class, LongWritable.class, new Path(args[0]));

		return job;
	}

	/**
	 * @return
	 */
	private static int printUsage() {
		System.out.println("Usage: " + NAME + " [generic-options] <output-path>");
		System.out.println();
		System.out.println("Configurable Properties:");
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
		int res = ToolRunner.run(new Configuration(), new CrashCount(), args);
		System.exit(res);
	}

}
