package com.mozilla.socorro.hadoop;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.regex.Pattern;

import org.apache.commons.lang.StringUtils;
import org.apache.commons.math.stat.descriptive.DescriptiveStatistics;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FileStatus;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.client.Scan;
import org.apache.hadoop.hbase.io.ImmutableBytesWritable;
import org.apache.hadoop.hbase.mapreduce.TableMapper;
import org.apache.hadoop.hbase.util.Bytes;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.util.GenericOptionsParser;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;

import com.mozilla.hadoop.hbase.mapreduce.MultiScanTableMapReduceUtil;
import com.mozilla.util.DateUtil;

public class RawDumpSize implements Tool {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(RawDumpSize.class);
	
	private static final String NAME = "RawDumpSize";
	private Configuration conf;

	// HBase table and column names
	private static final String TABLE_NAME_CRASH_REPORTS = "crash_reports";
	private static final byte[] RAW_DATA_BYTES = "raw_data".getBytes();
	private static final byte[] DUMP_BYTES = "dump".getBytes();
	private static final byte[] PROCESSED_DATA_BYTES = Bytes.toBytes("processed_data");
	private static final byte[] JSON_BYTES = Bytes.toBytes("json");
	
	// Configuration fields
	private static final String START_DATE = "start.date";
	private static final String END_DATE = "end.date";
	private static final String START_TIME = "start.time";
	private static final String END_TIME = "end.time";
	
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
			try {
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
			} catch (OutOfMemoryError e) {
				LOG.error("Out of memory encountered", e);
				context.getCounter(ReportStats.OOM_ERROR).increment(1L);
			}
		}
		
	}	

	/**
	 * Generates an array of scans for different salted ranges for the given dates
	 * @param startDate
	 * @param endDate
	 * @return
	 */
	public static Scan[] generateScans(Calendar startCal, Calendar endCal) {
		SimpleDateFormat rowsdf = new SimpleDateFormat("yyMMdd");
		
		ArrayList<Scan> scans = new ArrayList<Scan>();		
		String[] salts = new String[] { "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f" };
		
		long endTime = DateUtil.getEndTimeAtResolution(endCal.getTimeInMillis(), Calendar.DATE);
		
		while (startCal.getTimeInMillis() < endTime) {
			int d = Integer.parseInt(rowsdf.format(startCal.getTime()));
			
			for (int i=0; i < salts.length; i++) {
				Scan s = new Scan();
				// this caching number is selected by 64MB / Mean JSON Size
				s.setCaching(100);
				// disable block caching
				s.setCacheBlocks(false);
				// only looking for meta and processed json data
				s.addColumn(RAW_DATA_BYTES, DUMP_BYTES);
				s.addColumn(PROCESSED_DATA_BYTES, JSON_BYTES);
				
				s.setStartRow(Bytes.toBytes(salts[i] + String.format("%06d", d)));
				s.setStopRow(Bytes.toBytes(salts[i] + String.format("%06d", d + 1)));
				System.out.println("Adding start-stop range: " + salts[i] + String.format("%06d", d) + " - " + salts[i] + String.format("%06d", d + 1));
				
				scans.add(s);
			}
			
			startCal.add(Calendar.DATE, 1);
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
		conf.setLong(END_TIME, endCal.getTimeInMillis());
		
		//conf.set("mapred.child.java.opts", "-Xmx2048m");
		Job job = new Job(getConf());
		job.setJobName(NAME);
		job.setJarByClass(RawDumpSize.class);
		
		// input table configuration
		Scan[] scans = generateScans(startCal, endCal);
		MultiScanTableMapReduceUtil.initMultiScanTableMapperJob(TABLE_NAME_CRASH_REPORTS, scans, RawDumpSizeMapper.class, Text.class, IntWritable.class, job);

		job.setOutputKeyClass(Text.class);
		job.setOutputValueClass(IntWritable.class);
		job.setNumReduceTasks(0);
		
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