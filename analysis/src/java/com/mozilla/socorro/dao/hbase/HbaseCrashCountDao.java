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

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.Date;
import java.util.Map;
import java.util.NavigableMap;
import java.util.regex.Pattern;

import org.apache.hadoop.hbase.HBaseConfiguration;
import org.apache.hadoop.hbase.client.Get;
import org.apache.hadoop.hbase.client.HTable;
import org.apache.hadoop.hbase.client.HTablePool;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.util.Bytes;

import com.google.inject.Singleton;
import com.mozilla.socorro.CorrelationReport;
import com.mozilla.socorro.dao.CrashCountDao;

@Singleton
public class HbaseCrashCountDao implements CrashCountDao {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(HbaseCrashCountDao.class);
	
	private static final String TABLE_NAME = "crash_counts";
	
	private final HTablePool pool;
	private final Pattern shortKeyPattern;
	
	public HbaseCrashCountDao() throws IOException {
		HBaseConfiguration hbaseConfig = new HBaseConfiguration();		
		pool = new HTablePool(hbaseConfig, 1024);
		
		shortKeyPattern = Pattern.compile("\\p{Punct}|\\s");
	}
	
	private byte[] makeRowKey(Date date, String product, String version, String os, String signature) throws IOException {		
		if ("Firefox".equals(product)) {
			product = "FF";
		} else if ("Thunderbird".equals(product)) {
			product = "TB";
		} else if ("SeaMonkey".equals(product)) {
			product = "SM";
		}
		
		version = shortKeyPattern.matcher(version).replaceAll("");
		os = shortKeyPattern.matcher(os).replaceAll("");
		
		ByteArrayOutputStream baos = new ByteArrayOutputStream();
		baos.write(Bytes.toBytes(date.getTime()));
		baos.write(Bytes.toBytes(product));
		baos.write(Bytes.toBytes(version));
		baos.write(Bytes.toBytes(os));
		if (signature != null) {
			signature = shortKeyPattern.matcher(signature).replaceAll("");
			baos.write(Bytes.toBytes(signature));
		}
		
		return baos.toByteArray();
	}

	public void incrementCounts(Date date, String product, String version, String os, String signature, String arch, Map<String,String> moduleVersions, Map<String,String> addonVersions) throws IOException {
		HTable table = null;
		try {
			table = pool.getTable(TABLE_NAME);
			
			// increment os -> cpu info
			table.incrementColumnValue(makeRowKey(date, product, version, os, null), Bytes.toBytes("arch"), Bytes.toBytes(arch), 1L);
			// increment os -> sig -> cpu info
			table.incrementColumnValue(makeRowKey(date, product, version, os, signature), Bytes.toBytes("arch"), Bytes.toBytes(arch), 1L);
			
			for (Map.Entry<String, String> entry : moduleVersions.entrySet()) {
				String module = entry.getKey();
				String moduleVersion = entry.getValue();
				// increment os -> module
				// increment os -> module -> version
				table.incrementColumnValue(makeRowKey(date, product, version, os, null), Bytes.toBytes("module"), Bytes.toBytes(module), 1L);
				table.incrementColumnValue(makeRowKey(date, product, version, os, null), Bytes.toBytes("module_with_version"), Bytes.toBytes(module + "\u0002" + moduleVersion), 1L);
				
				// increment os -> sig -> module
				// increment os -> sig -> module -> version
				table.incrementColumnValue(makeRowKey(date, product, version, os, signature), Bytes.toBytes("module"), Bytes.toBytes(module), 1L);
				table.incrementColumnValue(makeRowKey(date, product, version, os, signature), Bytes.toBytes("module_with_version"), Bytes.toBytes(module + "\u0002" + moduleVersion), 1L);
			}
			
			for (Map.Entry<String, String> entry : addonVersions.entrySet()) {
				String addon = entry.getKey();
				String addonVersion = entry.getValue();
				// increment os -> addon
				// increment os -> addon -> version
				table.incrementColumnValue(makeRowKey(date, product, version, os, null), Bytes.toBytes("addon"), Bytes.toBytes(addon), 1L);
				table.incrementColumnValue(makeRowKey(date, product, version, os, null), Bytes.toBytes("addon_with_version"), Bytes.toBytes(addon + "\u0002" + addonVersion), 1L);
				// increment os -> sig -> addon
				// increment os -> sig -> addon -> version
				table.incrementColumnValue(makeRowKey(date, product, version, os, signature), Bytes.toBytes("addon"), Bytes.toBytes(addon), 1L);
				table.incrementColumnValue(makeRowKey(date, product, version, os, signature), Bytes.toBytes("addon_with_version"), Bytes.toBytes(addon + "\u0002" + addonVersion), 1L);
			}
		} finally {
			if (table != null) {
				pool.putTable(table);
			}
		}
	}
	
	public CorrelationReport getReport(Date date, String product, String version, String os, String signature) throws IOException {
		CorrelationReport report = new CorrelationReport(product, version, os, signature);
		
		HTable table = null;
		try {
			table = pool.getTable(TABLE_NAME);
			Get sigGet = new Get(makeRowKey(date, product, version, os, signature));
			Result sigResult = table.get(sigGet);
			if (sigResult != null && !sigResult.isEmpty()) {
				NavigableMap<byte[],byte[]> nm = sigResult.getFamilyMap(Bytes.toBytes("arch"));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String archCores = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					report.coreCountAdjustOrPut(archCores, (int)count);
				}
				
				nm = sigResult.getFamilyMap(Bytes.toBytes("module"));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String module = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					report.moduleAdjustOrPut(module, (int)count);
				}
				
				nm = sigResult.getFamilyMap(Bytes.toBytes("module_with_version"));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String moduleVersion = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					report.moduleVersionAdjustOrPut(moduleVersion, (int)count);
				}
				
				nm = sigResult.getFamilyMap(Bytes.toBytes("addon"));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String addon = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					report.addonAdjustOrPut(addon, (int)count);
				}
				
				nm = sigResult.getFamilyMap(Bytes.toBytes("addon_with_version"));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String addonVerison = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					report.addonVersionAdjustOrPut(addonVerison, (int)count);
				}
			}
		
			Get osGet = new Get(makeRowKey(date, product, version, os, null));
			Result osResult = table.get(osGet);
			if (osResult != null && !osResult.isEmpty()) {
				NavigableMap<byte[],byte[]> nm = osResult.getFamilyMap(Bytes.toBytes("arch"));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String archCores = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					report.osCoreCountAdjustOrPut(archCores, (int)count);
				}
				
				nm = osResult.getFamilyMap(Bytes.toBytes("module"));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String module = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					report.osModuleCountAdjustOrPut(module, (int)count);
				}
				
				nm = osResult.getFamilyMap(Bytes.toBytes("module_with_version"));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String moduleVersion = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					report.osModuleVersionCountAdjustOrPut(moduleVersion, (int)count);
				}
				
				nm = osResult.getFamilyMap(Bytes.toBytes("addon"));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String addon = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					report.osAddonCountAdjustOrPut(addon, (int)count);
				}
				
				nm = osResult.getFamilyMap(Bytes.toBytes("addon_with_version"));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String addonVersion = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					report.osAddonVersionCountAdjustOrPut(addonVersion, (int)count);
				}
			}
		} finally {
			if (table != null) {
				pool.putTable(table);
			}
		}
		
		return report;
	}
	
}
