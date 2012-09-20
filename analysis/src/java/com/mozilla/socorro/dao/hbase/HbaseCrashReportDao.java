/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package com.mozilla.socorro.dao.hbase;

import java.io.IOException;
import java.util.Calendar;
import java.util.Map;
import java.util.UUID;

import org.apache.hadoop.hbase.client.HTableInterface;
import org.apache.hadoop.hbase.client.HTablePool;
import org.apache.hadoop.hbase.client.Put;
import org.apache.hadoop.hbase.util.Bytes;

public class HbaseCrashReportDao {

	private static final int DEFAULT_DEPTH = 2;

	private HTablePool pool;

	public HbaseCrashReportDao(HTablePool pool) {
		this.pool = pool;
	}

	public String generateOOID(long millis) {
		return generateOOID(millis, DEFAULT_DEPTH);
	}

	public String generateOOID(long millis, int depth) {
		if (depth < 1 || depth > 4) {
			depth = DEFAULT_DEPTH;
		}

		Calendar cal = Calendar.getInstance();
		cal.setTimeInMillis(millis);

		String uuid = UUID.randomUUID().toString();
		String dateStr = String.format("%d%d%d", new Object[] { cal.get(Calendar.YEAR) % 100, cal.get(Calendar.MONTH) + 1, cal.get(Calendar.DATE) });

		StringBuilder sb = new StringBuilder();
		sb.append(uuid.substring(0, 1));
		sb.append(dateStr);
		sb.append(uuid.substring(0, uuid.length() - 7));
		sb.append(depth);
		sb.append(dateStr);

		return sb.toString();
	}

	public String insert(Map<String, String> fields, byte[] dump) throws IOException {
		String ooid = null;
		HTableInterface table = null;
		try {
			table = pool.getTable("crash_reports_test");
			ooid = generateOOID(System.currentTimeMillis());
			Put p = new Put(Bytes.toBytes(ooid));
			for (Map.Entry<String, String> field : fields.entrySet()) {
				p.add(Bytes.toBytes("meta_data"), Bytes.toBytes(field.getKey()), Bytes.toBytes(field.getValue()));
			}
			p.add(Bytes.toBytes("raw_data"), Bytes.toBytes("dump"), dump);

			table.put(p);
		} finally {
			pool.putTable(table);
		}

		return ooid;
	}

}
