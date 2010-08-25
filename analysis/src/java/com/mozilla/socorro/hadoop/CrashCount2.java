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
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

import org.apache.commons.lang.StringUtils;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.client.Scan;
import org.apache.hadoop.hbase.io.ImmutableBytesWritable;
import org.apache.hadoop.hbase.mapreduce.TableMapper;
import org.apache.hadoop.hbase.util.Bytes;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.mapreduce.lib.output.MultipleOutputs;
import org.apache.hadoop.mapreduce.lib.output.TextOutputFormat;
import org.apache.hadoop.mapreduce.lib.reduce.LongSumReducer;
import org.apache.hadoop.util.GenericOptionsParser;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;
import org.codehaus.jackson.JsonParseException;
import org.codehaus.jackson.map.JsonMappingException;
import org.codehaus.jackson.map.ObjectMapper;
import org.codehaus.jackson.type.TypeReference;

import com.mozilla.hadoop.hbase.mapreduce.MultiScanTableMapReduceUtil;
import com.mozilla.socorro.dao.hbase.HbaseCrashCountDao;
import com.mozilla.util.DateUtil;

public class CrashCount2 implements Tool {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(CrashCount2.class);
	
	private static final String NAME = "CrashCount2";
	private Configuration conf;

	// HBase table and column names
	private static final String TABLE_NAME_CRASH_REPORTS = "crash_reports";
	private static final byte[] PROCESSED_DATA_BYTES = "processed_data".getBytes();
	private static final byte[] JSON_BYTES = "json".getBytes();
	
	// Configuration fields
	private static final String START_DATE = "start.date";
	private static final String END_DATE = "end.date";
	private static final String START_TIME = "start.time";
	private static final String END_TIME = "end.time";
	
	// Crash JSON fields
	private static final String PRODUCT = "product";
	private static final String VERSION = "version";
	private static final String OS_NAME = "os_name";
	private static final String SIGNATURE = "signature";
	private static final String REASON = "reason";
	private static final String DUMP = "dump";
	private static final String DATE_PROCESSED = "date_processed";
	private static final String CPU_PATTERN = "CPU|";
	private static final String MODULE_PATTERN = "Module|";
	private static final String ADDONS = "addons";
	
	// Table Column Families
	//private static final String PRODUCT = "product";
	private static final String PRODUCT_VERSION = "product_version";
	private static final String OS = "os";
	//private static final String SIGNATURE = "signature";
	private static final String QUALIFIER_NAME = "name";
	private static final String ARCH = "arch";
	private static final String MODULE_WITH_VERSION = "module_with_version";
	private static final String ADDON_WITH_VERSION = "addon_with_version";
	
	// Table Column Qualifiers
	private static final String COUNT = "count";
	
	private static final String KEY_DELIMITER = "\u0001";
	private static final String MODULE_INFO_DELIMITER = "\u0002";
	private static final String COLUMN_DELIMITER = "\u0003";
	
	public static class CrashCount2Mapper extends TableMapper<Text, LongWritable> {

		public enum ReportStats { JSON_PARSE_EXCEPTION, JSON_MAPPING_EXCEPTION, JSON_BYTES_NULL, DATE_PARSE_EXCEPTION, REQUIRED_FIELD_BLANK, PROCESSED }

		private Text outputKey;
		private LongWritable one;
		
		private HbaseCrashCountDao ccDao;	
		private ObjectMapper jsonMapper;
		private Pattern newlinePattern;
		private Pattern pipePattern;
		private SimpleDateFormat sdf;
		private SimpleDateFormat rowSdf;
		private long startTime;
		private long endTime;
		private MultipleOutputs mos;
		
		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Mapper#setup(org.apache.hadoop.mapreduce.Mapper.Context)
		 */
		@SuppressWarnings("unchecked")
		public void setup(Context context) {
			outputKey = new Text();
			one = new LongWritable(1);
			
			mos = new MultipleOutputs(context);
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
		 * @see org.apache.hadoop.mapreduce.Mapper#cleanup(org.apache.hadoop.mapreduce.Mapper.Context)
		 */
		public void cleanup(Context context) throws InterruptedException, IOException {
			if (mos != null) {
				mos.close();
			}
		}
		
		private String normalize(String s) {
			s = StringUtils.deleteWhitespace(s);
			s = StringUtils.remove(s, KEY_DELIMITER);
			s = StringUtils.remove(s, MODULE_INFO_DELIMITER);
			s = StringUtils.remove(s, COLUMN_DELIMITER);
			
			return s;
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
				if (crash.containsKey(PRODUCT)) {
					product = (String)crash.get(PRODUCT);
				}
				if (crash.containsKey(VERSION)) {
					productVersion = (String)crash.get(VERSION);
				}
				
				// Set the value to the date
				String dateProcessed = (String)crash.get(DATE_PROCESSED);
				long crashTime = sdf.parse(dateProcessed).getTime();
				// Filter if the processed date is not within our window
				if (crashTime < startTime || crashTime > endTime) {
					return;
				}
				
				String osName = (String)crash.get(OS_NAME);
				if (osName == null) {
					return;
				}
				
				String signame = (String)crash.get(SIGNATURE);
				if (signame != null) {				
					signame = signame + "|" + crash.get(REASON);
				} else {
					signame = "(no signature)";
				}
				
				String arch = null;
				Map<String, String> moduleVersions = new HashMap<String,String>();
				for (String dumpline : newlinePattern.split((String)crash.get(DUMP))) {
					if (dumpline.startsWith(CPU_PATTERN)) {
						String[] dumplineSplits = pipePattern.split(dumpline);
						arch = String.format("%s with %s cores", new Object[] { dumplineSplits[1], dumplineSplits[3] });
					} else if (dumpline.startsWith(MODULE_PATTERN)) {
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
						
						moduleVersions.put(normalize(moduleName), normalize(version));
					}
				}

				Map<String, String> addonVersions = new HashMap<String,String>();
				List<Object> addons = (ArrayList<Object>)crash.get(ADDONS);
				if (addons != null) {
					for (Object addon : addons) {
						List<String> addonList = (ArrayList<String>)addon;
						String addonName = addonList.get(0);
						String version = addonList.get(1);
						
						addonVersions.put(normalize(addonName), normalize(version));
					}
				}
				
				if (!StringUtils.isBlank(product) && !StringUtils.isBlank(productVersion) &&
					!StringUtils.isBlank(osName) && !StringUtils.isBlank(signame)) {
					
					Calendar cal = Calendar.getInstance();
					cal.setTimeInMillis(DateUtil.getTimeAtResolution(crashTime, Calendar.DATE));
					String dateStr = rowSdf.format(cal.getTime());

					String sigRowKey = new String(ccDao.makeRowKey(dateStr, product, productVersion, osName, signame, true));
					String osRowKey = new String(ccDao.makeRowKey(dateStr, product, productVersion, osName, null, true));
					
					// os name/product/product_version
					outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { osRowKey, OS, QUALIFIER_NAME }));
					mos.write("strings", outputKey, new Text(osName));
					outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { osRowKey, PRODUCT, product }));
					mos.write("strings", outputKey, new Text(osName));
					outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { osRowKey, PRODUCT_VERSION, productVersion }));
					mos.write("strings", outputKey, new Text(osName));
					
					// signature name/product/product_version
					outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { sigRowKey, SIGNATURE, QUALIFIER_NAME }));
					mos.write("strings", outputKey, new Text(signame));
					outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { sigRowKey, PRODUCT, product }));
					mos.write("strings", outputKey, new Text(osName));
					outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { sigRowKey, PRODUCT_VERSION, productVersion }));
					mos.write("strings", outputKey, new Text(osName));	
					
					// os count
					outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { osRowKey, OS, COUNT }));
					context.write(outputKey, one);
					
					// os -> cpu info
					outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { osRowKey, ARCH, arch }));
					context.write(outputKey, one);
					
					// os -> signature count
					outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { sigRowKey, SIGNATURE, COUNT }));
					context.write(outputKey, one);
					
					// os -> sig -> cpu info
					outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { sigRowKey, ARCH, arch }));
					context.write(outputKey, one);
					
					for (Map.Entry<String, String> entry : moduleVersions.entrySet()) {
						String module = entry.getKey();
						String moduleVersion = entry.getValue();
						String moduleQualifier = null;
						if (StringUtils.isBlank(moduleVersion)) {
							moduleQualifier = module;
						} else {
							moduleQualifier = module + MODULE_INFO_DELIMITER + moduleVersion;
						}

						// os -> module -> version
						outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { osRowKey, MODULE_WITH_VERSION, moduleQualifier }));
						context.write(outputKey, one);
						
						// os -> sig -> module -> version
						outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { sigRowKey, MODULE_WITH_VERSION, moduleQualifier }));
						context.write(outputKey, one);
					}
					
					for (Map.Entry<String, String> entry : addonVersions.entrySet()) {
						String addon = entry.getKey();
						String addonVersion = entry.getValue();
						String addonQualifier = null;
						if (StringUtils.isBlank(addonVersion)) {
							addonQualifier = addon;
						} else {
							addonQualifier = addon + MODULE_INFO_DELIMITER + addonVersion;
						}

						// os -> addon -> version
						outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { osRowKey, ADDON_WITH_VERSION, addonQualifier }));
						context.write(outputKey, one);

						// os -> sig -> addon -> version
						outputKey.set(String.format("%s" + KEY_DELIMITER + "%s" + COLUMN_DELIMITER + "%s", new Object[] { sigRowKey, ADDON_WITH_VERSION, addonQualifier }));
						context.write(outputKey, one);
					}
					
					context.getCounter(ReportStats.PROCESSED).increment(1L);
				} else {
					context.getCounter(ReportStats.REQUIRED_FIELD_BLANK).increment(1L);
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
	 * Generates an array of scans for different salted ranges for the given dates
	 * @param startDateAsInt 
	 * @param endDateAsInt
	 * @return
	 */
	public static Scan[] generateScans(int startDateAsInt, int endDateAsInt) {
		ArrayList<Scan> scans = new ArrayList<Scan>();		
		String[] salts = new String[] { "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f" };
		for (int d = startDateAsInt; d <= endDateAsInt; d++) {
			for (int i=0; i < salts.length; i++) {
				Scan s = new Scan();
				// this caching number is selected by 64MB / Mean JSON Size
				s.setCaching(1788);
				// disable block caching
				s.setCacheBlocks(false);
				// only looking for processed data
				s.addFamily(PROCESSED_DATA_BYTES);
				
				s.setStartRow(Bytes.toBytes(salts[i] + String.format("%06d", d)));
				s.setStopRow(Bytes.toBytes(salts[i] + String.format("%06d", d + 1)));
				
				scans.add(s);
			}
		}
		
		return scans.toArray(new Scan[scans.size()]);
	}
	
	/**
	 * @param args
	 * @return
	 * @throws IOException
	 * @throws ParseException 
	 */
	public Job initJob(String[] args) throws IOException, ParseException {
		// Set both start/end time and start/stop row
		Calendar cal = Calendar.getInstance();
		
		SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMdd");
		SimpleDateFormat rowsdf = new SimpleDateFormat("yyMMdd");
		
		String startDate = conf.get(START_DATE);
		String endDate = conf.get(END_DATE);
		int startDateAsInt = 0;
		int endDateAsInt = 0;
		if (!StringUtils.isBlank(startDate)) {
			Date d = sdf.parse(startDate);
			conf.setLong(START_TIME, d.getTime());
			startDateAsInt = Integer.parseInt(rowsdf.format(d));
		} else {
			conf.setLong(START_TIME, cal.getTimeInMillis());
			startDateAsInt = Integer.parseInt(rowsdf.format(cal.getTime()));
		}
		if (!StringUtils.isBlank(endDate)) {
			Date d = sdf.parse(endDate);
			conf.setLong(END_TIME, d.getTime());
			endDateAsInt = Integer.parseInt(rowsdf.format(d));
		} else {
			conf.setLong(END_TIME, cal.getTimeInMillis());
			endDateAsInt = Integer.parseInt(rowsdf.format(cal.getTime()));
		}
		
		Job job = new Job(getConf());
		job.setJobName(NAME);
		job.setJarByClass(CrashCount2.class);
		
		// input table configuration
		Scan[] scans = generateScans(startDateAsInt, endDateAsInt);
		MultiScanTableMapReduceUtil.initMultiScanTableMapperJob(TABLE_NAME_CRASH_REPORTS, scans, CrashCount2Mapper.class, Text.class, LongWritable.class, job);
		
		MultipleOutputs.addNamedOutput(job, "strings", TextOutputFormat.class, Text.class, Text.class);
		
		job.setCombinerClass(LongSumReducer.class);
		job.setReducerClass(LongSumReducer.class);
		job.setOutputKeyClass(Text.class);
		job.setOutputValueClass(LongWritable.class);
		
		FileOutputFormat.setOutputPath(job, new Path(args[0]));
		
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
		int res = ToolRunner.run(new Configuration(), new CrashCount2(), args);
		System.exit(res);
	}
	
}
