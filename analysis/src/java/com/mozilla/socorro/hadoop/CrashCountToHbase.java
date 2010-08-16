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
import java.util.Iterator;
import java.util.regex.Pattern;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.hbase.client.HTable;
import org.apache.hadoop.hbase.client.Put;
import org.apache.hadoop.hbase.regionserver.NoSuchColumnFamilyException;
import org.apache.hadoop.hbase.util.Bytes;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.util.GenericOptionsParser;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;

public class CrashCountToHbase implements Tool {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(CrashCountToHbase.class);
	
	private static final String NAME = "CrashCountToHbase";
	private Configuration conf;

	// HBase table and column names
	private static final String TABLE_NAME = "crash_counts";
	private static final String PRODUCT = "product";
	private static final String PRODUCT_VERSION = "product_version";
	private static final String OS = "os";
	private static final String SIGNATURE = "signature";
	private static final String QUALIFIER_NAME = "name";
	
	private static final String KEY_DELIMITER = "\u0001";
	private static final String COLUMN_DELIMITER = "\u0003";
	private static final String COUNT_DELIMITER = "\u0004";
	
	public static class CrashCountToHBaseMapper extends Mapper<LongWritable, Text, Text, Text> {

		public enum ReportStats { UNEXPECTED_KV_LENGTH, UNEXPECTED_KEY_SPLIT_LENGTH, PROCESSED }

		private Text outputKey;
		private Text outputValue;
		
		private Pattern tabPattern;
		private Pattern keyPattern;
		
		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Mapper#setup(org.apache.hadoop.mapreduce.Mapper.Context)
		 */
		public void setup(Context context) {
			outputKey = new Text();
			outputValue = new Text();
			
			tabPattern = Pattern.compile("\t");
			keyPattern = Pattern.compile(KEY_DELIMITER);
		}
		
		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Mapper#map(KEYIN, VALUEIN, org.apache.hadoop.mapreduce.Mapper.Context)
		 */
		public void map(LongWritable key, Text value, Context context) throws InterruptedException, IOException {
			String[] kv = tabPattern.split(value.toString());
			if (kv.length == 2) {
				String[] keySplits = keyPattern.split(kv[0]);
				if (keySplits.length == 2) {
					outputKey.set(keySplits[0]);
					outputValue.set(keySplits[1] + COUNT_DELIMITER + kv[1]);
					context.write(outputKey, outputValue);
					context.getCounter(ReportStats.PROCESSED).increment(1L);
				} else {
					context.getCounter(ReportStats.UNEXPECTED_KEY_SPLIT_LENGTH).increment(1L);
					LOG.error("Wrong number of splits for value: " + kv[0]);
				}
			} else {
				context.getCounter(ReportStats.UNEXPECTED_KV_LENGTH).increment(1L);
				LOG.error("KV length unexpected: " + value.toString());
			}
		}
		
	}	
	
	public static class CrashCountToHBaseReducer extends Reducer<Text, Text, Text, Text> {
		
		public enum ReportStats { UNEXPECTED_VALUE_SPLIT_LENGTH, UNEXPECTED_COLUMN_SPLIT_LENGTH, NUMBER_FORMAT_EXCEPTION, PROCESSED, PUT_EXCEPTION }
		
		private Pattern columnPattern;
		private Pattern valuePattern;
		private HTable table;
		
		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Reducer#setup(org.apache.hadoop.mapreduce.Reducer.Context)
		 */
		public void setup(Context context) {
			//valuePattern = Pattern.compile("(.+?):(.+?)" + COUNT_DELIMITER + "(.+)");
			valuePattern = Pattern.compile(COUNT_DELIMITER);
			columnPattern = Pattern.compile(COLUMN_DELIMITER);
			try {
				table = new HTable(TABLE_NAME);
			} catch (IOException e) {
				throw new RuntimeException("Could not instantiate HTable", e);
			}
		}
		
		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Reducer#cleanup(org.apache.hadoop.mapreduce.Reducer.Context)
		 */
		public void cleanup(Context context) {
			try {
				if (table != null) {
					table.close();
				}
			} catch (IOException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}
		}
		
		/* (non-Javadoc)
		 * @see org.apache.hadoop.mapreduce.Reducer#reduce(KEYIN, java.lang.Iterable, org.apache.hadoop.mapreduce.Reducer.Context)
		 */
		public void reduce(Text key, Iterable<Text> values, Context context) throws IOException {
			Iterator<Text> iter = values.iterator();
			byte[] rowKey = Bytes.toBytes(key.toString());
			Put p = new Put(rowKey);
			while (iter.hasNext()) {
				String v = iter.next().toString();
				String[] valueSplits = valuePattern.split(v);
				if (valueSplits.length == 2) {
					String[] familyQualifierSplits = columnPattern.split(valueSplits[0]);
					if (valueSplits.length == 2) {			
						String family = familyQualifierSplits[0];
						String qualifier = familyQualifierSplits[1];
						
						byte[] valueBytes = null;
						if ((SIGNATURE.equals(family) && QUALIFIER_NAME.equals(qualifier)) ||
							(OS.equals(family) && QUALIFIER_NAME.equals(qualifier)) ||
							PRODUCT.equals(family) || PRODUCT_VERSION.equals(family)) {
							if (p.has(Bytes.toBytes(family), Bytes.toBytes(qualifier))) {
								continue;
							}
							
							if (SIGNATURE.equals(family) && QUALIFIER_NAME.equals(qualifier)) {
								valueBytes = Bytes.toBytes(valueSplits[1]);	
							} else {
								valueBytes = Bytes.toBytes(true);
							}
						} else {
							try {
								long count = Long.parseLong(valueSplits[1]);
								valueBytes = Bytes.toBytes(count);
							} catch (NumberFormatException e) {
								context.getCounter(ReportStats.NUMBER_FORMAT_EXCEPTION).increment(1L);
								LOG.error("Was expecting a number for family: " + family + " qualifier: " + qualifier);
								continue;
							}
						}
						
						try {
							p.add(Bytes.toBytes(family), Bytes.toBytes(qualifier), valueBytes);
						} catch (IllegalArgumentException e) {
							context.getCounter(ReportStats.PUT_EXCEPTION).increment(1L);
							LOG.error("Exception during Put for value: " + v + " family: " + family + " qualifier: " + qualifier, e);
						}
					} else {
						context.getCounter(ReportStats.UNEXPECTED_COLUMN_SPLIT_LENGTH).increment(1L);
					}
				} else {
					context.getCounter(ReportStats.UNEXPECTED_VALUE_SPLIT_LENGTH).increment(1L);
				}
			}
			
			try {
				table.put(p);
				context.getCounter(ReportStats.PROCESSED).increment(1L);
			} catch (NoSuchColumnFamilyException e) {
				context.getCounter(ReportStats.PUT_EXCEPTION).increment(1L);
				e.printStackTrace();
			} catch (IllegalArgumentException e) {
				context.getCounter(ReportStats.PUT_EXCEPTION).increment(1L);
				e.printStackTrace();
			}
		}
		
	}
	
	/**
	 * @param args
	 * @return
	 * @throws IOException
	 * @throws ParseException 
	 */
	public Job initJob(String[] args) throws IOException {
		Job job = new Job(getConf());
		job.setJobName(NAME);
		job.setJarByClass(CrashCountToHbase.class);

		FileInputFormat.addInputPath(job, new Path(args[0]));
		
		job.setMapperClass(CrashCountToHBaseMapper.class);
		job.setReducerClass(CrashCountToHBaseReducer.class);
		job.setMapOutputKeyClass(Text.class);
		job.setMapOutputValueClass(Text.class);
		job.setOutputKeyClass(Text.class);
		job.setOutputValueClass(Text.class);
		
		FileOutputFormat.setOutputPath(job, new Path(args[1]));
		
		return job;
	}

	/**
	 * @return
	 */
	private static int printUsage() {
		System.out.println("Usage: " + NAME + " <input-path> <output-path>");
		System.out.println();
		GenericOptionsParser.printGenericCommandUsage(System.out);
		
		return -1;
	}
	
	/* (non-Javadoc)
	 * @see org.apache.hadoop.util.Tool#run(java.lang.String[])
	 */
	public int run(String[] args) throws Exception {
		if (args.length != 2) {
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
		int res = ToolRunner.run(new Configuration(), new CrashCountToHbase(), args);
		System.exit(res);
	}
	

}
