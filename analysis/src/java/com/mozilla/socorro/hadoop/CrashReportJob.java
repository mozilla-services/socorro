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
import java.util.Calendar;
import java.util.Map;

import org.apache.commons.lang.StringUtils;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.hbase.client.Scan;
import org.apache.hadoop.hbase.mapreduce.TableMapper;
import org.apache.hadoop.hbase.util.Bytes;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

import com.mozilla.hadoop.hbase.mapreduce.MultiScanTableMapReduceUtil;
import com.mozilla.util.DateUtil;

public class CrashReportJob {

	// Configuration fields
	public static final String START_DATE = "start.date";
	public static final String END_DATE = "end.date";
	public static final String START_TIME = "start.time";
	public static final String END_TIME = "end.time";

	public static final String PRODUCT_FILTER = "product.filter";
	public static final String RELEASE_FILTER = "release.filter";
	public static final String OS_FILTER = "os.filter";
	public static final String OS_VERSION_FILTER = "os.version.filter";

	// HBase Table and Columns
	public static final String TABLE_NAME_CRASH_REPORTS = "crash_reports";
	public static final byte[] RAW_DATA_BYTES = "raw_data".getBytes();
	public static final byte[] META_DATA_BYTES = Bytes.toBytes("meta_data");
	public static final byte[] PROCESSED_DATA_BYTES = "processed_data".getBytes();
	public static final byte[] DUMP_BYTES = "dump".getBytes();
	public static final byte[] JSON_BYTES = "json".getBytes();

	// Meta JSON Fields
	public static final String META_JSON_CRASH_TIME = "CrashTime";
	public static final String META_JSON_PRODUCT_NAME = "ProductName";
	public static final String META_JSON_PRODUCT_VERSION = "Version";
	public static final String META_JSON_HANG_ID = "HangID";
	public static final String META_JSON_PROCESS_TYPE = "ProcessType";

	// Processed JSON Fields
	public static final String PROCESSED_JSON_PRODUCT = "product";
	public static final String PROCESSED_JSON_VERSION = "version";
	public static final String PROCESSED_JSON_OS_NAME = "os_name";
	public static final String PROCESSED_JSON_OS_VERSION = "os_version";
	public static final String PROCESSED_JSON_SIGNATURE = "signature";
	public static final String PROCESSED_JSON_REASON = "reason";
	public static final String PROCESSED_JSON_DUMP = "dump";
	public static final String PROCESSED_JSON_DATE_PROCESSED = "date_processed";
	public static final String PROCESSED_JSON_CPU_PATTERN = "CPU|";
	public static final String PROCESSED_JSON_MODULE_PATTERN = "Module|";
	public static final String PROCESSED_JSON_ADDONS = "addons";

	/**
	 * @param args
	 * @return
	 * @throws IOException
	 * @throws ParseException
	 */
	public static Job initJob(String jobName, Configuration conf, Class<?> mainClass, Class<? extends TableMapper> mapperClass,
							  Class<? extends Reducer> combinerClass, Class<? extends Reducer> reducerClass, Map<byte[], byte[]> columns,
							  Class<? extends WritableComparable> keyOut, Class<? extends Writable> valueOut, Path outputPath) throws IOException, ParseException {
		// Set both start/end time and start/stop row
		Calendar startCal = Calendar.getInstance();
		Calendar endCal = Calendar.getInstance();

		SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMdd");

		String startDateStr = conf.get(START_DATE);
		String endDateStr = conf.get(END_DATE);
		if (!StringUtils.isBlank(startDateStr)) {
			startCal.setTime(sdf.parse(startDateStr));
		}
		if (!StringUtils.isBlank(endDateStr)) {
			endCal.setTime(sdf.parse(endDateStr));
		}

		conf.setLong(START_TIME, startCal.getTimeInMillis());
		conf.setLong(END_TIME, DateUtil.getEndTimeAtResolution(endCal.getTimeInMillis(), Calendar.DATE));

		Job job = new Job(conf);
		job.setJobName(jobName);
		job.setJarByClass(mainClass);

		// input table configuration
		Scan[] scans = MultiScanTableMapReduceUtil.generateScans(startCal, endCal, columns, 100, false);
		MultiScanTableMapReduceUtil.initMultiScanTableMapperJob(TABLE_NAME_CRASH_REPORTS, scans, mapperClass, keyOut, valueOut, job);

		if (combinerClass != null) {
			job.setCombinerClass(combinerClass);
		}

		if (reducerClass != null) {
			job.setReducerClass(reducerClass);
		} else {
			job.setNumReduceTasks(0);
		}

		FileOutputFormat.setOutputPath(job, outputPath);

		return job;
	}

}
