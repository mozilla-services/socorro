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

import static com.mozilla.socorro.hadoop.CrashReportJob.DUMP_BYTES;
import static com.mozilla.socorro.hadoop.CrashReportJob.END_DATE;
import static com.mozilla.socorro.hadoop.CrashReportJob.JSON_BYTES;
import static com.mozilla.socorro.hadoop.CrashReportJob.PROCESSED_DATA_BYTES;
import static com.mozilla.socorro.hadoop.CrashReportJob.RAW_DATA_BYTES;
import static com.mozilla.socorro.hadoop.CrashReportJob.START_DATE;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.text.ParseException;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Pattern;

import org.apache.commons.math.stat.descriptive.DescriptiveStatistics;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FileStatus;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.io.ImmutableBytesWritable;
import org.apache.hadoop.hbase.mapreduce.TableMapper;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.util.GenericOptionsParser;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;

public class RawDumpSize implements Tool {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(RawDumpSize.class);
	
	private static final String NAME = "RawDumpSize";
	private Configuration conf;
	
	private static final String KEY_DELIMITER = "\t";
	
	public static class RawDumpSizeMapper extends TableMapper<Text, IntWritable> {

		public enum ReportStats { RAW_BYTES_NULL, PROCESSED_BYTES_NULL, OOM_ERROR }
		
		private Text outputKey;
		private IntWritable outputValue;
		
		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Mapper#setup(org.apache.hadoop.mapreduce.Mapper.Context)
		 */
		public void setup(Context context) {
			outputKey = new Text();
			outputValue = new IntWritable();
		}

		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Mapper#map(KEYIN, VALUEIN, org.apache.hadoop.mapreduce.Mapper.Context)
		 */
		public void map(ImmutableBytesWritable key, Result result, Context context) throws InterruptedException, IOException {
			String rowKey = new String(result.getRow());
			StringBuilder keyPrefix = new StringBuilder("20");
			keyPrefix.append(rowKey.substring(1, 7)).append(KEY_DELIMITER);
			
			byte[] valueBytes = result.getValue(RAW_DATA_BYTES, DUMP_BYTES);
			if (valueBytes == null) {
				context.getCounter(ReportStats.RAW_BYTES_NULL).increment(1L);
			} else {
				outputKey.set(keyPrefix.toString() + "raw");
				outputValue.set(valueBytes.length);
				context.write(outputKey, outputValue);
			}
			
			valueBytes = result.getValue(PROCESSED_DATA_BYTES, JSON_BYTES);
			if (valueBytes == null) {
				context.getCounter(ReportStats.PROCESSED_BYTES_NULL).increment(1L);
			} else {
				outputKey.set(keyPrefix.toString() + "processed");
				outputValue.set(valueBytes.length);
				context.write(outputKey, outputValue);
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
		columns.put(RAW_DATA_BYTES, DUMP_BYTES);
		columns.put(PROCESSED_DATA_BYTES, JSON_BYTES);
		Job job = CrashReportJob.initJob(NAME, getConf(), RawDumpSize.class, RawDumpSizeMapper.class, null, null, columns, Text.class, IntWritable.class, new Path(args[0]));
		
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
			FileSystem hdfs = null;
			DescriptiveStatistics rawStats = new DescriptiveStatistics();
			long rawTotal = 0L;
			DescriptiveStatistics processedStats = new DescriptiveStatistics();
			long processedTotal = 0L;
			try {
				hdfs = FileSystem.get(job.getConfiguration());
				Pattern tabPattern = Pattern.compile("\t");
				for (FileStatus status : hdfs.listStatus(FileOutputFormat.getOutputPath(job))) {
					if (!status.isDir()) {
						BufferedReader reader = null;
						try {
							reader = new BufferedReader(new InputStreamReader(hdfs.open(status.getPath())));
							String line = null;
							while ((line = reader.readLine()) != null) {
								String[] splits = tabPattern.split(line);
								int byteSize = Integer.parseInt(splits[2]);
								if ("raw".equals(splits[1])) {
									rawStats.addValue(byteSize);
									rawTotal += byteSize;
								} else if ("processed".equals(splits[1])) {
									processedStats.addValue(byteSize);
									processedTotal += byteSize;
								}
							}
						} finally {
							if (reader != null) {
								reader.close();
							}
						}
					}
				}
			} finally {
				if (hdfs != null) {
					hdfs.close();
				}
			}
			
			System.out.println("===== " + job.getConfiguration().get(START_DATE) + " raw_data:dump =====");
			System.out.println(String.format("Min: %.02f Max: %.02f Mean: %.02f", rawStats.getMin(), rawStats.getMax(), rawStats.getMean()));
			System.out.println(String.format("1st Quartile: %.02f 2nd Quartile: %.02f 3rd Quartile: %.02f", rawStats.getPercentile(25.0d), rawStats.getPercentile(50.0d), rawStats.getPercentile(75.0d)));
			System.out.println("Total Bytes: " + rawTotal);
			System.out.println("===== " + job.getConfiguration().get(START_DATE) + " processed_data:json =====");
			System.out.println(String.format("Min: %.02f Max: %.02f Mean: %.02f", processedStats.getMin(), processedStats.getMax(), processedStats.getMean()));
			System.out.println(String.format("1st Quartile: %.02f 2nd Quartile: %.02f 3rd Quartile: %.02f", processedStats.getPercentile(25.0d), processedStats.getPercentile(50.0d), processedStats.getPercentile(75.0d)));
			System.out.println("Total Bytes: " + processedTotal);
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
		int res = ToolRunner.run(new Configuration(), new RawDumpSize(), args);
		System.exit(res);
	}

}