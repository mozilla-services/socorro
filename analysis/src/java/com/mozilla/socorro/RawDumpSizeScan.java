/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package com.mozilla.socorro;

import java.io.IOException;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import org.apache.commons.lang.StringUtils;
import org.apache.commons.math.stat.descriptive.DescriptiveStatistics;
import org.apache.hadoop.hbase.client.HTable;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.client.ResultScanner;
import org.apache.hadoop.hbase.client.Scan;
import org.apache.hadoop.hbase.io.ImmutableBytesWritable;
import org.apache.hadoop.hbase.util.Bytes;

import com.mozilla.util.DateUtil;

public class RawDumpSizeScan {

	private static final String TABLE_NAME_CRASH_REPORTS = "crash_reports";
	private static final byte[] RAW_DATA_BYTES = "raw_data".getBytes();
	private static final byte[] DUMP_BYTES = "dump".getBytes();

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
				s.setCaching(4);
				// disable block caching
				s.setCacheBlocks(false);
				s.addColumn(RAW_DATA_BYTES, DUMP_BYTES);

				s.setStartRow(Bytes.toBytes(salts[i] + String.format("%06d", d)));
				s.setStopRow(Bytes.toBytes(salts[i] + String.format("%06d", d + 1)));
				System.out.println("Adding start-stop range: " + salts[i] + String.format("%06d", d) + " - " + salts[i] + String.format("%06d", d + 1));

				scans.add(s);
			}

			startCal.add(Calendar.DATE, 1);
		}

		return scans.toArray(new Scan[scans.size()]);
	}

	public static void main(String[] args) throws ParseException {
		String startDateStr = args[0];
		String endDateStr = args[1];

		// Set both start/end time and start/stop row
		Calendar startCal = Calendar.getInstance();
		Calendar endCal = Calendar.getInstance();

		SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMdd");

		if (!StringUtils.isBlank(startDateStr)) {
			startCal.setTime(sdf.parse(startDateStr));
		}
		if (!StringUtils.isBlank(endDateStr)) {
			endCal.setTime(sdf.parse(endDateStr));
		}

		DescriptiveStatistics stats = new DescriptiveStatistics();
		long numNullRawBytes = 0L;
		HTable table = null;
		Map<String,Integer> rowValueSizeMap = new HashMap<String, Integer>();
		try {
			table = new HTable(TABLE_NAME_CRASH_REPORTS);
			Scan[] scans = generateScans(startCal, endCal);
			for (Scan s : scans) {
				ResultScanner rs = table.getScanner(s);
				Iterator<Result> iter = rs.iterator();
				while(iter.hasNext()) {
					Result r = iter.next();
					ImmutableBytesWritable rawBytes = r.getBytes();
					//length = r.getValue(RAW_DATA_BYTES, DUMP_BYTES);
					if (rawBytes != null) {
						int length = rawBytes.getLength();
						if (length > 20971520) {
							rowValueSizeMap.put(new String(r.getRow()), length);
						}
						stats.addValue(length);
					} else {
						numNullRawBytes++;
					}

					if (stats.getN() % 10000 == 0) {
						System.out.println("Processed " + stats.getN());
						System.out.println(String.format("Min: %.02f Max: %.02f Mean: %.02f", stats.getMin(), stats.getMax(), stats.getMean()));
						System.out.println(String.format("1st Quartile: %.02f 2nd Quartile: %.02f 3rd Quartile: %.02f", stats.getPercentile(25.0d), stats.getPercentile(50.0d), stats.getPercentile(75.0d)));
						System.out.println("Number of large entries: " + rowValueSizeMap.size());
					}
				}
				rs.close();
			}

			System.out.println("Finished Processing!");
			System.out.println(String.format("Min: %.02f Max: %.02f Mean: %.02f", stats.getMin(), stats.getMax(), stats.getMean()));
			System.out.println(String.format("1st Quartile: %.02f 2nd Quartile: %.02f 3rd Quartile: %.02f", stats.getPercentile(25.0d), stats.getPercentile(50.0d), stats.getPercentile(75.0d)));

			for (Map.Entry<String, Integer> entry : rowValueSizeMap.entrySet()) {
				System.out.println(String.format("RowId: %s => Length: %d", entry.getKey(), entry.getValue()));
			}
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} finally {
			if (table != null) {
				try {
					table.close();
				} catch (IOException e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				}
			}
		}
	}

}
