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
			table = pool.getTable("crash_reports");
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
