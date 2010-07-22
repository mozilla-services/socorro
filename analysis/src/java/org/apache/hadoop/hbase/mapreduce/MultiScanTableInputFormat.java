package org.apache.hadoop.hbase.mapreduce;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.conf.Configurable;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.hbase.HBaseConfiguration;
import org.apache.hadoop.hbase.client.HTable;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.client.ResultScanner;
import org.apache.hadoop.hbase.client.Scan;
import org.apache.hadoop.hbase.io.ImmutableBytesWritable;
import org.apache.hadoop.hbase.util.Bytes;
import org.apache.hadoop.hbase.util.Pair;
import org.apache.hadoop.mapreduce.InputSplit;
import org.apache.hadoop.mapreduce.JobContext;
import org.apache.hadoop.mapreduce.RecordReader;
import org.apache.hadoop.mapreduce.TaskAttemptContext;
import org.apache.hadoop.util.StringUtils;

/**
 * Similar to TableInputFormat except this is meant for an array of Scan objects that can
 * be used to delimit row-key ranges.  This allows the usage of hashed dates to be prepended
 * to row keys so that hbase won't create hotspots based on dates, while minimizing the amount
 * of data that must be read during a MapReduce job for a given day.
 * 
 * Note: Only the first Scan object is used as a template.  The rest are only used for ranges.
 * @author Daniel Einspanjer
 * @author Xavier Stevens
 *
 */
public class MultiScanTableInputFormat extends org.apache.hadoop.mapreduce.InputFormat<ImmutableBytesWritable, Result> implements Configurable {

	private final Log LOG = LogFactory.getLog(MultiScanTableInputFormat.class);

	/** Job parameter that specifies the input table. */
	public static final String INPUT_TABLE = "hbase.mapreduce.inputtable";
	
	/**
	 * Base-64 encoded array of scanners.
	 */
	public static final String SCANS = "hbase.mapreduce.scans";
	
	private Configuration conf = null;
	private HTable table = null;
	private Scan[] scans = null;
	private TableRecordReader trr = null;
	
	/* (non-Javadoc)
	 * @see org.apache.hadoop.mapreduce.InputFormat#createRecordReader(org.apache.hadoop.mapreduce.InputSplit, org.apache.hadoop.mapreduce.TaskAttemptContext)
	 */
	@Override
	public RecordReader<ImmutableBytesWritable, Result> createRecordReader(InputSplit split, TaskAttemptContext context) throws IOException, InterruptedException {
		if (scans == null) {
			throw new IOException("No scans were provided");
		}
		if (table == null) {
			throw new IOException("No table was provided.");
		}
		if (trr == null) {
			trr = new TableRecordReader();
		}
		
		TableSplit tSplit = (TableSplit)split;
		
		Scan scan = new Scan(scans[0]);		
		scan.setStartRow(tSplit.getStartRow());
		scan.setStopRow(tSplit.getEndRow());
		
		trr.setScan(scan);
		trr.setHTable(table);
		trr.init();
		
		return trr;
	}

	/* (non-Javadoc)
	 * @see org.apache.hadoop.mapreduce.InputFormat#getSplits(org.apache.hadoop.mapreduce.JobContext)
	 */
	@Override
	public List<InputSplit> getSplits(JobContext context) throws IOException, InterruptedException {
		if (table == null) {
			throw new IOException("No table was provided.");
		}
		
		Pair<byte[][], byte[][]> keys = table.getStartEndKeys();
		if (keys == null || keys.getFirst() == null || keys.getFirst().length == 0) {
			throw new IOException("Expecting at least one region.");
		}

		Set<InputSplit> splits = new HashSet<InputSplit>();
		for (int i = 0; i < keys.getFirst().length; i++) {
			String regionLocation = table.getRegionLocation(keys.getFirst()[i]).getServerAddress().getHostname();
			
			for (Scan s : scans) {
				byte[] startRow = s.getStartRow();
				byte[] stopRow = s.getStopRow();
				
				// determine if the given start an stop key fall into the region
				if ((startRow.length == 0 || keys.getSecond()[i].length == 0 || Bytes.compareTo(startRow, keys.getSecond()[i]) < 0) && 
					 (stopRow.length == 0 || Bytes.compareTo(stopRow, keys.getFirst()[i]) > 0)) {
					byte[] splitStart = startRow.length == 0 || Bytes.compareTo(keys.getFirst()[i], startRow) >= 0 ? keys.getFirst()[i]	: startRow;
					byte[] splitStop = (stopRow.length == 0 || Bytes.compareTo(keys.getSecond()[i], stopRow) <= 0) 
										&& keys.getSecond()[i].length > 0 ? keys.getSecond()[i] : stopRow;
					InputSplit split = new TableSplit(table.getTableName(), splitStart, splitStop, regionLocation);
					splits.add(split);
				}
			}
		}
		
		return new ArrayList<InputSplit>(splits);
	}

	/* (non-Javadoc)
	 * @see org.apache.hadoop.conf.Configurable#getConf()
	 */
	@Override
	public Configuration getConf() {
		return conf;
	}

	/* (non-Javadoc)
	 * @see org.apache.hadoop.conf.Configurable#setConf(org.apache.hadoop.conf.Configuration)
	 */
	@Override
	public void setConf(Configuration conf) {
		this.conf = conf;
		
		String tableName = conf.get(INPUT_TABLE);
		try {
			setHTable(new HTable(new HBaseConfiguration(conf), tableName));
		} catch (Exception e) {
			LOG.error(StringUtils.stringifyException(e));
		}
		
		Scan[] scans = null;
		if (conf.get(SCANS) != null) {
			try {
				scans = MultiScanTableMapReduceUtil.convertStringToScanArray(conf.get(SCANS));
			} catch (IOException e) {
				LOG.error("An error occurred.", e);
			}
		} else {
			scans = new Scan[] { new Scan() };
		}
		
		setScans(scans);
	}

	/**
	 * Allows subclasses to get the {@link HTable}.
	 */
	protected HTable getHTable() {
		return this.table;
	}

	/**
	 * Allows subclasses to set the {@link HTable}.
	 * 
	 * @param table
	 *            The table to get the data from.
	 */
	protected void setHTable(HTable table) {
		this.table = table;
	}
	
	/**
	 * @return
	 */
	public Scan[] getScans() {
		return scans;
	}

	/**
	 * @param scans The scans to use as boundaries.
	 */
	public void setScans(Scan[] scans) {
		this.scans = scans;
	}
	
	/**
	 * Iterate over an HBase table data, return (ImmutableBytesWritable, Result)
	 * pairs.
	 */
	protected class TableRecordReader extends RecordReader<ImmutableBytesWritable, Result> {

		private ResultScanner scanner = null;
		private Scan scan = null;
		private HTable htable = null;
		private byte[] lastRow = null;
		private ImmutableBytesWritable key = null;
		private Result value = null;

		/**
		 * Restart from survivable exceptions by creating a new scanner.
		 * 
		 * @param firstRow
		 *            The first row to start at.
		 * @throws IOException
		 *             When restarting fails.
		 */
		public void restart(byte[] firstRow) throws IOException {
			Scan newScan = new Scan(scan);
			newScan.setStartRow(firstRow);
			this.scanner = this.htable.getScanner(newScan);
		}

		/**
		 * Build the scanner. Not done in constructor to allow for extension.
		 * 
		 * @throws IOException
		 *             When restarting the scan fails.
		 */
		public void init() throws IOException {
			restart(scan.getStartRow());
		}

		/**
		 * Sets the HBase table.
		 * 
		 * @param htable
		 *            The {@link HTable} to scan.
		 */
		public void setHTable(HTable htable) {
			this.htable = htable;
		}

		/**
		 * Sets the scan defining the actual details like columns etc.
		 * 
		 * @param scan
		 *            The scan to set.
		 */
		public void setScan(Scan scan) {
			this.scan = scan;
		}

		/**
		 * Closes the split.
		 * 
		 * @see org.apache.hadoop.mapreduce.RecordReader#close()
		 */
		@Override
		public void close() {
			this.scanner.close();
		}

		/**
		 * Returns the current key.
		 * 
		 * @return The current key.
		 * @throws IOException
		 * @throws InterruptedException
		 *             When the job is aborted.
		 * @see org.apache.hadoop.mapreduce.RecordReader#getCurrentKey()
		 */
		@Override
		public ImmutableBytesWritable getCurrentKey() throws IOException, InterruptedException {
			return key;
		}

		/**
		 * Returns the current value.
		 * 
		 * @return The current value.
		 * @throws IOException
		 *             When the value is faulty.
		 * @throws InterruptedException
		 *             When the job is aborted.
		 * @see org.apache.hadoop.mapreduce.RecordReader#getCurrentValue()
		 */
		@Override
		public Result getCurrentValue() throws IOException, InterruptedException {
			return value;
		}

		/**
		 * Initializes the reader.
		 * 
		 * @param inputsplit
		 *            The split to work with.
		 * @param context
		 *            The current task context.
		 * @throws IOException
		 *             When setting up the reader fails.
		 * @throws InterruptedException
		 *             When the job is aborted.
		 * @see org.apache.hadoop.mapreduce.RecordReader#initialize(org.apache.hadoop.mapreduce.InputSplit,
		 *      org.apache.hadoop.mapreduce.TaskAttemptContext)
		 */
		@Override
		public void initialize(InputSplit inputsplit, TaskAttemptContext context) throws IOException,
				InterruptedException {
		}

		/**
		 * Positions the record reader to the next record.
		 * 
		 * @return <code>true</code> if there was another record.
		 * @throws IOException
		 *             When reading the record failed.
		 * @throws InterruptedException
		 *             When the job was aborted.
		 * @see org.apache.hadoop.mapreduce.RecordReader#nextKeyValue()
		 */
		@Override
		public boolean nextKeyValue() throws IOException, InterruptedException {
			if (key == null)
				key = new ImmutableBytesWritable();
			if (value == null)
				value = new Result();
			try {
				value = this.scanner.next();
			} catch (IOException e) {
				LOG.debug("recovered from " + StringUtils.stringifyException(e));
				restart(lastRow);
				scanner.next(); // skip presumed already mapped row
				value = scanner.next();
			}
			if (value != null && value.size() > 0) {
				key.set(value.getRow());
				lastRow = key.get();
				return true;
			}
			return false;
		}

		/**
		 * The current progress of the record reader through its data.
		 * 
		 * @return A number between 0.0 and 1.0, the fraction of the data read.
		 * @see org.apache.hadoop.mapreduce.RecordReader#getProgress()
		 */
		@Override
		public float getProgress() {
			// Depends on the total number of tuples
			return 0;
		}
	}
}
