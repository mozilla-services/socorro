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
import java.net.URLDecoder;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.NavigableMap;
import java.util.regex.Pattern;

import org.apache.commons.lang.StringUtils;
import org.apache.hadoop.hbase.HBaseConfiguration;
import org.apache.hadoop.hbase.client.Get;
import org.apache.hadoop.hbase.client.HTable;
import org.apache.hadoop.hbase.client.HTablePool;
import org.apache.hadoop.hbase.client.Put;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.client.ResultScanner;
import org.apache.hadoop.hbase.client.Scan;
import org.apache.hadoop.hbase.filter.CompareFilter;
import org.apache.hadoop.hbase.filter.RegexStringComparator;
import org.apache.hadoop.hbase.filter.RowFilter;
import org.apache.hadoop.hbase.util.Bytes;

import com.google.inject.Singleton;
import com.mozilla.socorro.CorrelationReport;
import com.mozilla.socorro.OperatingSystem;
import com.mozilla.socorro.Signature;
import com.mozilla.socorro.dao.CrashCountDao;

@Singleton
public class HbaseCrashCountDao implements CrashCountDao {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(HbaseCrashCountDao.class);
	
	private static final String TABLE_NAME = "crash_counts";
	
	// Table Column Families
	private static final String DATE = "date";
	private static final String PRODUCT = "product";
	private static final String PRODUCT_VERSION = "product_version";
	private static final String OS = "os";
	private static final String SIGNATURE = "signature";
	private static final String ARCH = "arch";
	private static final String MODULE = "module";
	private static final String MODULE_WITH_VERSION = "module_with_version";
	private static final String ADDON = "addon";
	private static final String ADDON_WITH_VERSION = "addon_with_version";
	
	// Table Column Qualifiers
	private static final String NAME = "name";
	private static final String COUNT = "count";
	
	// Safe delimiter for appending/splitting module names with versions
	private static final String MODULE_INFO_DELIMITER = "\u0002";
	private static final Pattern SIG_REASON_DELIMITER = Pattern.compile("\\|");
	
	private static final int MAX_REPORTS = 100;
	
	private final HTablePool pool;
	private final Pattern shortKeyPattern;
	private final Map<String,String> productShortNameMap;
	
	public HbaseCrashCountDao() throws IOException {
		HBaseConfiguration hbaseConfig = new HBaseConfiguration();		
		pool = new HTablePool(hbaseConfig, 1024);
		
		shortKeyPattern = Pattern.compile("\\p{Punct}|\\s");
		
		productShortNameMap = new HashMap<String,String>();
		productShortNameMap.put("Firefox", "FF");
		productShortNameMap.put("Thunderbird", "TB");
		productShortNameMap.put("SeaMonkey", "SM");
		productShortNameMap.put("Camino", "CM");
	}
	
	private byte[] makeRowKey(String date, String product, String version, String os, String signature) throws IOException {		

		if (productShortNameMap.containsKey(product)) {
			product = productShortNameMap.get(product);
		}
		
		version = shortKeyPattern.matcher(version).replaceAll("");
		os = shortKeyPattern.matcher(os).replaceAll("");

		ByteArrayOutputStream baos = new ByteArrayOutputStream();
		baos.write(Bytes.toBytes(date));
		baos.write(Bytes.toBytes(product));
		baos.write(Bytes.toBytes(version));
		baos.write(Bytes.toBytes(os));
		if (!StringUtils.isBlank(signature)) {
			signature = shortKeyPattern.matcher(signature).replaceAll("");
			baos.write(Bytes.toBytes(signature));
		}
		
		return baos.toByteArray();
	}

	public void incrementCounts(String date, String product, String version, String os, String signature, String arch, Map<String,String> moduleVersions, Map<String,String> addonVersions) throws IOException {
		HTable table = null;
		try {
			table = pool.getTable(TABLE_NAME);
			
			byte[] osRowKey = makeRowKey(date, product, version, os, null);
			byte[] sigRowKey = makeRowKey(date, product, version, os, signature);

			// Fill in main info for OS key to allow better scans by different dimensions
			// only need to do this once for efficiency
			if (!table.exists(new Get(osRowKey))) {
				Put put = new Put(osRowKey);
				put.add(Bytes.toBytes(DATE), System.currentTimeMillis(), Bytes.toBytes(date));
				put.add(Bytes.toBytes(PRODUCT), Bytes.toBytes(product), Bytes.toBytes(true));
				put.add(Bytes.toBytes(PRODUCT_VERSION), Bytes.toBytes(version), Bytes.toBytes(true));
				put.add(Bytes.toBytes(OS), Bytes.toBytes(os), Bytes.toBytes(true));
				
				table.put(put);
			}
			
			// Fill in main info for signature key to allow better scans by different dimensions
			// only need to do this once for efficiency
			if (!table.exists(new Get(sigRowKey))) {
				Put put = new Put(sigRowKey);
				put.add(Bytes.toBytes(DATE), System.currentTimeMillis(), Bytes.toBytes(date));
				put.add(Bytes.toBytes(PRODUCT), Bytes.toBytes(product), Bytes.toBytes(true));
				put.add(Bytes.toBytes(PRODUCT_VERSION), Bytes.toBytes(version), Bytes.toBytes(true));
				put.add(Bytes.toBytes(OS), Bytes.toBytes(os), Bytes.toBytes(true));
				put.add(Bytes.toBytes(SIGNATURE), Bytes.toBytes(NAME), Bytes.toBytes(signature));
				
				table.put(put);
			}
			
			// increment os count
			table.incrementColumnValue(osRowKey, Bytes.toBytes(OS), Bytes.toBytes(COUNT), 1L);
			// increment os -> cpu info
			table.incrementColumnValue(osRowKey, Bytes.toBytes(ARCH), Bytes.toBytes(arch), 1L);
			// increment os -> signature count
			table.incrementColumnValue(sigRowKey, Bytes.toBytes(SIGNATURE), Bytes.toBytes(COUNT), 1L);
			// increment os -> sig -> cpu info
			table.incrementColumnValue(sigRowKey, Bytes.toBytes(ARCH), Bytes.toBytes(arch), 1L);
			
			for (Map.Entry<String, String> entry : moduleVersions.entrySet()) {
				String module = entry.getKey();
				String moduleVersion = entry.getValue();
				// increment os -> module
				// increment os -> module -> version
				table.incrementColumnValue(osRowKey, Bytes.toBytes(MODULE), Bytes.toBytes(module), 1L);
				table.incrementColumnValue(osRowKey, Bytes.toBytes(MODULE_WITH_VERSION), Bytes.toBytes(module + MODULE_INFO_DELIMITER + moduleVersion), 1L);
				
				// increment os -> sig -> module
				// increment os -> sig -> module -> version
				table.incrementColumnValue(sigRowKey, Bytes.toBytes(MODULE), Bytes.toBytes(module), 1L);
				table.incrementColumnValue(sigRowKey, Bytes.toBytes(MODULE_WITH_VERSION), Bytes.toBytes(module + MODULE_INFO_DELIMITER + moduleVersion), 1L);
			}
			
			for (Map.Entry<String, String> entry : addonVersions.entrySet()) {
				String addon = entry.getKey();
				String addonVersion = entry.getValue();
				// increment os -> addon
				// increment os -> addon -> version
				table.incrementColumnValue(osRowKey, Bytes.toBytes(ADDON), Bytes.toBytes(addon), 1L);
				table.incrementColumnValue(osRowKey, Bytes.toBytes(ADDON_WITH_VERSION), Bytes.toBytes(addon + MODULE_INFO_DELIMITER + addonVersion), 1L);
				// increment os -> sig -> addon
				// increment os -> sig -> addon -> version
				table.incrementColumnValue(sigRowKey, Bytes.toBytes(ADDON), Bytes.toBytes(addon), 1L);
				table.incrementColumnValue(sigRowKey, Bytes.toBytes(ADDON_WITH_VERSION), Bytes.toBytes(addon + MODULE_INFO_DELIMITER + addonVersion), 1L);
			}
		} finally {
			if (table != null) {
				pool.putTable(table);
			}
		}
	}
	
	public List<Signature> getTopCrashers(String date, String product, String version, String os) throws IOException {
		Scan scan = new Scan();
		String rowKeyExpr = "^" + new String(makeRowKey(date, product, version, os, null)) + ".+";
		RowFilter rowFilter = new RowFilter(CompareFilter.CompareOp.EQUAL, new RegexStringComparator(rowKeyExpr));
		scan.setFilter(rowFilter);
		
		// Want the values of these columns for filtered rows
		scan.addFamily(Bytes.toBytes(SIGNATURE));
		scan.addFamily(Bytes.toBytes(ARCH));
		scan.addFamily(Bytes.toBytes(MODULE));
		scan.addFamily(Bytes.toBytes(MODULE_WITH_VERSION));
		scan.addFamily(Bytes.toBytes(ADDON));
		scan.addFamily(Bytes.toBytes(ADDON_WITH_VERSION));
		
		List<Signature> signatures = new ArrayList<Signature>();
		
		HTable table = null;
		ResultScanner scanner = null;
		try {
			table = pool.getTable(TABLE_NAME);
			scanner = table.getScanner(scan);
			long resultCount = 0;
			for (Result r : scanner) {
				resultCount++;
				LOG.info("Returned row: " + new String(r.getRow()));
//				NavigableMap<byte[],NavigableMap<byte[],byte[]>> noVersionMap = r.getNoVersionMap();
//				if (noVersionMap != null) {
//					for (Map.Entry<byte[], NavigableMap<byte[], byte[]>> entry : noVersionMap.entrySet()) {
//						LOG.info(" family:" + new String(entry.getKey()));
//						for (Map.Entry<byte[], byte[]> qvEntry : entry.getValue().entrySet()) {
//							LOG.info("  qualifier: " + new String(qvEntry.getKey()));
//						}
//					}
//				}
				byte[] sigBytes = r.getValue(Bytes.toBytes(SIGNATURE), Bytes.toBytes(NAME));
				byte[] sigCountBytes = r.getValue(Bytes.toBytes(SIGNATURE), Bytes.toBytes(COUNT));
				if (sigBytes != null && sigCountBytes != null) {
					String signature = new String(sigBytes);
					Signature sig = new Signature(signature);
					sig.setCount((int)Bytes.toLong(sigCountBytes));
					
					NavigableMap<byte[],byte[]> nm = r.getFamilyMap(Bytes.toBytes(ARCH));
					for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
						String archCores = new String(entry.getKey());
						long count = Bytes.toLong(entry.getValue());
						
						sig.incrementCoreCount(archCores, (int)count);
					}

					nm = r.getFamilyMap(Bytes.toBytes(MODULE_WITH_VERSION));
					for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
						String moduleVersion = new String(entry.getKey());
						String[] splits = moduleVersion.split(MODULE_INFO_DELIMITER);
						long count = Bytes.toLong(entry.getValue());
						
						if (splits.length == 2) {
							sig.incrementModuleCount(splits[0], splits[1], (int)count);
						} else {
							sig.incrementModuleCount(moduleVersion, "", (int)count);
						}
					}
					
					nm = r.getFamilyMap(Bytes.toBytes(ADDON_WITH_VERSION));
					for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
						String addonVersion = new String(entry.getKey());
						String[] splits = addonVersion.split(MODULE_INFO_DELIMITER);
						long count = Bytes.toLong(entry.getValue());
						
						if (splits.length == 2) {
							sig.incrementAddonCount(splits[0], splits[1], (int)count);
						} else {
							sig.incrementAddonCount(addonVersion, "", (int)count);
						}
					}
					
					signatures.add(sig);
				}
			}
			
			LOG.info("Result Count: " + resultCount);
		} finally {
			if (scanner != null) {
				scanner.close();
			}
			
			if (table != null) {
				pool.putTable(table);
			}
		}
		
		Collections.sort(signatures, Collections.reverseOrder(new Comparator<Signature>() {

			public int compare(Signature s1, Signature s2) {
				return s1.getCount() < s2.getCount() ? -1 : s1.getCount() > s2.getCount() ? 1 : 0;
			}
			
		}));

		int maxIndex = 0;
		if (signatures.size() > 0) {
			maxIndex = signatures.size() < MAX_REPORTS ? signatures.size() : MAX_REPORTS;
		}
		
		return signatures.subList(0, maxIndex);
	}
	
	public CorrelationReport getReport(String date, String product, String version, String os, String signature) throws IOException {
		LOG.info("Date: " + date);
		LOG.info("Product: " + product);
		LOG.info("Version: " + version);
		LOG.info("OS: " + os);
		LOG.info("Signature: " + URLDecoder.decode(signature, "UTF-8"));
		signature = URLDecoder.decode(signature, "UTF-8");
		
		CorrelationReport report2 = new CorrelationReport(product, version, os);
		OperatingSystem osys = report2.getOs();
		
		HTable table = null;
		try {
			byte[] osRowKey = makeRowKey(date, product, version, os, null);
			byte[] sigRowKey = makeRowKey(date, product, version, os, signature);
			
			table = pool.getTable(TABLE_NAME);
			Get sigGet = new Get(sigRowKey);
			Result sigResult = table.get(sigGet);
			if (sigResult != null && !sigResult.isEmpty()) {
				Signature sig = null;
				String[] sigReason = SIG_REASON_DELIMITER.split(signature);
				// hang or plugin
				if (sigReason.length == 3) {
					sig = new Signature(sigReason[0] + " | " + sigReason[1], sigReason[2]);
				// normal signature and reason
				} else if (sigReason.length == 2) {
					sig = new Signature(sigReason[0], sigReason[1]);
				// signature with no reason?
				} else {
					sig = new Signature(signature);
				}
				
				int sigCount = (int)Bytes.toLong(sigResult.getValue(Bytes.toBytes(SIGNATURE), Bytes.toBytes(COUNT)));
				sig.setCount(sigCount);
				
				NavigableMap<byte[],byte[]> nm = sigResult.getFamilyMap(Bytes.toBytes(ARCH));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String archCores = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					sig.incrementCoreCount(archCores, (int)count);
				}
				
				nm = sigResult.getFamilyMap(Bytes.toBytes(MODULE_WITH_VERSION));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String moduleVersion = new String(entry.getKey());
					String[] splits = moduleVersion.split(MODULE_INFO_DELIMITER, 3);
					long count = Bytes.toLong(entry.getValue());
					
					if (splits.length == 2) {
						sig.incrementModuleCount(splits[0], splits[1], (int)count);
					} else {
						sig.incrementModuleCount(moduleVersion, "", (int)count);
					}
				}
				
				nm = sigResult.getFamilyMap(Bytes.toBytes(ADDON_WITH_VERSION));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String addonVersion = new String(entry.getKey());
					String[] splits = addonVersion.split(MODULE_INFO_DELIMITER, 3);
					long count = Bytes.toLong(entry.getValue());
					
					if (splits.length == 2) {
						sig.incrementAddonCount(splits[0], splits[1], (int)count);
					} else {
						sig.incrementAddonCount(addonVersion, "", (int)count);
					}
				}
				
				osys.addSignature(signature, sig);
			}
		
			Get osGet = new Get(osRowKey);
			Result osResult = table.get(osGet);
			if (osResult != null && !osResult.isEmpty()) {
				
				int osCount = (int)Bytes.toLong(osResult.getValue(Bytes.toBytes(OS), Bytes.toBytes(COUNT)));
				osys.setCount(osCount);
				
				NavigableMap<byte[],byte[]> nm = osResult.getFamilyMap(Bytes.toBytes(ARCH));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String archCores = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					osys.incrementCoreCount(archCores, (int)count);
				}
				
				nm = osResult.getFamilyMap(Bytes.toBytes(MODULE_WITH_VERSION));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String moduleVersion = new String(entry.getKey());
					String[] splits = moduleVersion.split(MODULE_INFO_DELIMITER, 3);
					long count = Bytes.toLong(entry.getValue());
				
					if (splits.length == 2) {
						osys.incrementModuleCount(splits[0], splits[1], (int)count);
					} else {
						osys.incrementModuleCount(moduleVersion, "", (int)count);
					}
				}
				
				nm = osResult.getFamilyMap(Bytes.toBytes(ADDON_WITH_VERSION));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String addonVersion = new String(entry.getKey());
					String[] splits = addonVersion.split(MODULE_INFO_DELIMITER, 3);
					long count = Bytes.toLong(entry.getValue());
					
					if (splits.length == 2) {
						osys.incrementAddonCount(splits[0], splits[1], (int)count);
					} else {
						osys.incrementAddonCount(addonVersion, "", (int)count);
					}
				}
				
				report2.setOs(osys);
			}
		} finally {
			if (table != null) {
				pool.putTable(table);
			}
		}
		
		return report2;
	}
	
}
