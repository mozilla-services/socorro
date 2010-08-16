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
import java.util.HashMap;
import java.util.Map;
import java.util.NavigableMap;
import java.util.regex.Pattern;

import org.apache.commons.lang.StringUtils;
import org.apache.hadoop.hbase.client.Get;
import org.apache.hadoop.hbase.client.HTable;
import org.apache.hadoop.hbase.client.HTablePool;
import org.apache.hadoop.hbase.client.Put;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.client.ResultScanner;
import org.apache.hadoop.hbase.client.Scan;
import org.apache.hadoop.hbase.filter.CompareFilter;
import org.apache.hadoop.hbase.filter.FilterList;
import org.apache.hadoop.hbase.filter.RegexStringComparator;
import org.apache.hadoop.hbase.filter.RowFilter;
import org.apache.hadoop.hbase.filter.SingleColumnValueFilter;
import org.apache.hadoop.hbase.util.Bytes;
import org.eclipse.jetty.util.log.Log;

import com.google.inject.Singleton;
import com.mozilla.socorro.CorrelationReport;
import com.mozilla.socorro.OperatingSystem;
import com.mozilla.socorro.Signature;
import com.mozilla.socorro.dao.CrashCountDao;

@Singleton
public class HbaseCrashCountDao implements CrashCountDao {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(HbaseCrashCountDao.class);
	
	public static final String TABLE_NAME = "crash_counts";
	
	// Table Column Families
	private static final byte[] DATE = Bytes.toBytes("date");
	private static final byte[] PRODUCT = Bytes.toBytes("product");
	private static final byte[] PRODUCT_VERSION = Bytes.toBytes("product_version");
	private static final byte[] OS = Bytes.toBytes("os");
	private static final byte[] SIGNATURE = Bytes.toBytes("signature");
	private static final byte[] ARCH = Bytes.toBytes("arch");
	private static final byte[] MODULE_WITH_VERSION = Bytes.toBytes("module_with_version");
	private static final byte[] ADDON_WITH_VERSION = Bytes.toBytes("addon_with_version");
	
	// Table Column Qualifiers
	private static final byte[] NAME = Bytes.toBytes("name");
	private static final byte[] COUNT = Bytes.toBytes("count");
	
	// Safe delimiter for appending/splitting module names with versions
	private static final String MODULE_INFO_DELIMITER = "\u0002";
	
	private final HTablePool pool;
	private final Pattern shortKeyPattern;
	private final Map<String,String> productShortNameMap;
	
	public HbaseCrashCountDao() throws IOException {		
		pool = new HTablePool();
		
		shortKeyPattern = Pattern.compile("\\p{Punct}|\\s");
		
		productShortNameMap = new HashMap<String,String>();
		productShortNameMap.put("Firefox", "FF");
		productShortNameMap.put("Thunderbird", "TB");
		productShortNameMap.put("SeaMonkey", "SM");
		productShortNameMap.put("Camino", "CM");
	}
	
	public byte[] makeRowKey(String date, String product, String version, String os, String signature, boolean hash) throws IOException {
		// calculate total length to use as a consistent hash char
		int totalLength = date.length() + product.length() + version.length() + os.length();
		if (signature != null) {
			totalLength += signature.length();
		}
		int hexMod = totalLength % 16;
		
		if (productShortNameMap.containsKey(product)) {
			product = productShortNameMap.get(product);
		}
		
		version = shortKeyPattern.matcher(version).replaceAll("");
		os = shortKeyPattern.matcher(os).replaceAll("");

		ByteArrayOutputStream baos = new ByteArrayOutputStream();
		if (hash) {
			baos.write(Bytes.toBytes(Integer.toHexString(hexMod)));
		}
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
	
	public void checkSignatureExists(byte[] sigRowKey, String product, String version, String os, String signature) throws IOException {
		HTable table = null;
		try {
			table = pool.getTable(TABLE_NAME);
			if (!table.exists(new Get(sigRowKey))) {
				Put put = new Put(sigRowKey);
//				put.add(DATE, System.currentTimeMillis(), Bytes.toBytes(date));
				put.add(PRODUCT, Bytes.toBytes(product), Bytes.toBytes(true));
				put.add(PRODUCT_VERSION, Bytes.toBytes(version), Bytes.toBytes(true));
				put.add(OS, Bytes.toBytes(os), Bytes.toBytes(true));
				put.add(SIGNATURE, NAME, Bytes.toBytes(signature));
				
				table.put(put);
			}
		} finally {
			if (table != null) {
				pool.putTable(table);
			}
		}
	}

	public void checkOsExists(byte[] osRowKey, String product, String version, String os) throws IOException {
		HTable table = null;
		try {
			table = pool.getTable(TABLE_NAME);
			if (!table.exists(new Get(osRowKey))) {
				Put put = new Put(osRowKey);
//				put.add(DATE, System.currentTimeMillis(), Bytes.toBytes(date));
				put.add(PRODUCT, Bytes.toBytes(product), Bytes.toBytes(true));
				put.add(PRODUCT_VERSION, Bytes.toBytes(version), Bytes.toBytes(true));
				put.add(OS, Bytes.toBytes(os), Bytes.toBytes(true));
				
				table.put(put);
			}
		} finally {
			if (table != null) {
				pool.putTable(table);
			}
		}
	}
	
	public void incrementCounts(String date, String product, String version, String os, String signature, String arch, Map<String,String> moduleVersions, Map<String,String> addonVersions) throws IOException {
		HTable table = null;
		try {
			table = pool.getTable(TABLE_NAME);
			
			byte[] osRowKey = makeRowKey(date, product, version, os, null, true);
			byte[] sigRowKey = makeRowKey(date, product, version, os, signature, true);

			// Fill in main info for OS/signature key to allow better scans by different dimensions
			// only need to do this once for efficiency
			checkOsExists(osRowKey, product, version, os);
			checkSignatureExists(sigRowKey, product, version, os, signature);
			
			// increment os count
			table.incrementColumnValue(osRowKey, OS, COUNT, 1L);
			// increment os -> cpu info
			table.incrementColumnValue(osRowKey, ARCH, Bytes.toBytes(arch), 1L);
			// increment os -> signature count
			table.incrementColumnValue(sigRowKey, SIGNATURE, COUNT, 1L);
			// increment os -> sig -> cpu info
			table.incrementColumnValue(sigRowKey, ARCH, Bytes.toBytes(arch), 1L);
			
			for (Map.Entry<String, String> entry : moduleVersions.entrySet()) {
				String module = entry.getKey();
				String moduleVersion = entry.getValue();
				byte[] moduleQualifier = null;
				if (StringUtils.isBlank(moduleVersion)) {
					moduleQualifier = Bytes.toBytes(module);
				} else {
					moduleQualifier = Bytes.toBytes(module + MODULE_INFO_DELIMITER + moduleVersion);
				}

				// increment os -> module -> version
				table.incrementColumnValue(osRowKey, MODULE_WITH_VERSION, moduleQualifier, 1L);
				
				// increment os -> sig -> module -> version
				table.incrementColumnValue(sigRowKey, MODULE_WITH_VERSION, moduleQualifier, 1L);
			}
			
			for (Map.Entry<String, String> entry : addonVersions.entrySet()) {
				String addon = entry.getKey();
				String addonVersion = entry.getValue();
				byte[] addonQualifier = null;
				if (StringUtils.isBlank(addonVersion)) {
					addonQualifier = Bytes.toBytes(addon);
				} else {
					addonQualifier = Bytes.toBytes(addon + MODULE_INFO_DELIMITER + addonVersion);
				}

				// increment os -> addon -> version
				table.incrementColumnValue(osRowKey, ADDON_WITH_VERSION, addonQualifier, 1L);

				// increment os -> sig -> addon -> version
				table.incrementColumnValue(sigRowKey, ADDON_WITH_VERSION, addonQualifier, 1L);
			}
		} finally {
			if (table != null) {
				pool.putTable(table);
			}
		}
	}
	
	public CorrelationReport getTopCrashers(String date, String product, String version, String os) throws IOException {
		Scan scan = new Scan();
		FilterList filterList = new FilterList(FilterList.Operator.MUST_PASS_ALL);
		
		String rowKeyExpr = "^[a-zA-Z0-9]{1}" + new String(makeRowKey(date, product, version, os, null, false)) + ".+";
		RowFilter rowFilter = new RowFilter(CompareFilter.CompareOp.EQUAL, new RegexStringComparator(rowKeyExpr));
		filterList.addFilter(rowFilter);
		
		SingleColumnValueFilter productFilter = new SingleColumnValueFilter(PRODUCT, Bytes.toBytes(product), CompareFilter.CompareOp.EQUAL, Bytes.toBytes(true));
		SingleColumnValueFilter productVersionFilter = new SingleColumnValueFilter(PRODUCT_VERSION, Bytes.toBytes(version), CompareFilter.CompareOp.EQUAL, Bytes.toBytes(true));
		SingleColumnValueFilter osFilter = new SingleColumnValueFilter(OS, Bytes.toBytes(os), CompareFilter.CompareOp.EQUAL, Bytes.toBytes(true));
		filterList.addFilter(productFilter);
		filterList.addFilter(productVersionFilter);
		filterList.addFilter(osFilter);
		
		scan.setFilter(filterList);
		
		// Want the values of these columns for filtered rows
		scan.addFamily(SIGNATURE);
		scan.addFamily(ARCH);
		scan.addFamily(MODULE_WITH_VERSION);
		scan.addFamily(ADDON_WITH_VERSION);
		
		CorrelationReport report = new CorrelationReport(date, product, version, os);

		HTable table = null;
		ResultScanner scanner = null;
		try {
			table = pool.getTable(TABLE_NAME);
			scanner = table.getScanner(scan);
			long resultCount = 0;
			for (Result r : scanner) {
				OperatingSystem osys = report.getOs();
				
				resultCount++;
				if (Log.isDebugEnabled()) {
					LOG.debug("Returned row: " + new String(r.getRow()));
				}

				byte[] sigBytes = r.getValue(SIGNATURE, NAME);
				byte[] sigCountBytes = r.getValue(SIGNATURE, COUNT);
				if (sigBytes != null && sigCountBytes != null) {
					String rawSignature = new String(sigBytes);
					Signature sig = null;
					if (osys.getSignatures().containsKey(rawSignature)) {
						sig = osys.getSignatures().get(rawSignature);
					} else {
						sig = new Signature(rawSignature);
					}

					sig.setCount(sig.getCount() + (int)Bytes.toLong(sigCountBytes));
					
					NavigableMap<byte[],byte[]> nm = r.getFamilyMap(ARCH);
					for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
						String archCores = new String(entry.getKey());
						long count = Bytes.toLong(entry.getValue());
						
						sig.incrementCoreCount(archCores, (int)count);
					}

					nm = r.getFamilyMap(MODULE_WITH_VERSION);
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
					
					nm = r.getFamilyMap(ADDON_WITH_VERSION);
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

					osys.addSignature(sig.getName(), sig);
					report.setOs(osys);
				}
			}
			
			if (Log.isDebugEnabled()) {
				LOG.debug("Result Count: " + resultCount);
			}
			
			byte[] osRowKey = makeRowKey(date, product, version, os, null, true);
			Get osGet = new Get(osRowKey);
			Result osResult = table.get(osGet);
			if (osResult != null && !osResult.isEmpty()) {
				OperatingSystem osys = report.getOs();
				
				int osCount = (int)Bytes.toLong(osResult.getValue(OS, COUNT));
				osys.setCount(osCount);
				
				NavigableMap<byte[],byte[]> nm = osResult.getFamilyMap(ARCH);
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String archCores = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					osys.incrementCoreCount(archCores, (int)count);
				}
				
				nm = osResult.getFamilyMap(MODULE_WITH_VERSION);
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String moduleVersion = new String(entry.getKey());
					String[] splits = moduleVersion.split(MODULE_INFO_DELIMITER);
					long count = Bytes.toLong(entry.getValue());
				
					if (splits.length == 2) {
						osys.incrementModuleCount(splits[0], splits[1], (int)count);
					} else {
						osys.incrementModuleCount(moduleVersion, "", (int)count);
					}
				}
				
				nm = osResult.getFamilyMap(ADDON_WITH_VERSION);
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String addonVersion = new String(entry.getKey());
					String[] splits = addonVersion.split(MODULE_INFO_DELIMITER);
					long count = Bytes.toLong(entry.getValue());
					
					if (splits.length == 2) {
						osys.incrementAddonCount(splits[0], splits[1], (int)count);
					} else {
						osys.incrementAddonCount(addonVersion, "", (int)count);
					}
				}
				
				report.setOs(osys);
			}
		} finally {
			if (scanner != null) {
				scanner.close();
			}
			
			if (table != null) {
				pool.putTable(table);
			}
		}
		
		report.calculateModuleRatios();
		
		return report;
	}
	
	public CorrelationReport getReport(String date, String product, String version, String os, String signature) throws IOException {
		os = URLDecoder.decode(os, "UTF-8");
		signature = URLDecoder.decode(signature, "UTF-8");
		
		CorrelationReport report = new CorrelationReport(product, version, os);
		OperatingSystem osys = report.getOs();
		
		HTable table = null;
		try {
			byte[] osRowKey = makeRowKey(date, product, version, os, null, true);
			byte[] sigRowKey = makeRowKey(date, product, version, os, signature, true);
			
			if (LOG.isInfoEnabled()) {
				LOG.debug("Date: " + date);
				LOG.debug("Product: " + product);
				LOG.debug("Version: " + version);
				LOG.debug("OS: " + os);
				LOG.debug("Signature: " + signature);
				LOG.info("Sig Row Key: " + new String(sigRowKey));
			}
			
			table = pool.getTable(TABLE_NAME);
			Get sigGet = new Get(sigRowKey);
			Result sigResult = table.get(sigGet);
			if (sigResult != null && !sigResult.isEmpty()) {
				Signature sig = new Signature(signature);
				
				int sigCount = (int)Bytes.toLong(sigResult.getValue(SIGNATURE, COUNT));
				sig.setCount(sigCount);
				
				NavigableMap<byte[],byte[]> nm = sigResult.getFamilyMap(ARCH);
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String archCores = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					sig.incrementCoreCount(archCores, (int)count);
				}
				
				nm = sigResult.getFamilyMap(MODULE_WITH_VERSION);
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
				
				nm = sigResult.getFamilyMap(ADDON_WITH_VERSION);
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
				
				osys.addSignature(signature, sig);
			} else {
				LOG.warn("Signature result was empty for params: " + String.format("%s, %s, %s, %s, %s", date, product, version, os, signature));
			}
		
			Get osGet = new Get(osRowKey);
			Result osResult = table.get(osGet);
			if (osResult != null && !osResult.isEmpty()) {
				
				int osCount = (int)Bytes.toLong(osResult.getValue(OS, COUNT));
				osys.setCount(osCount);
				
				NavigableMap<byte[],byte[]> nm = osResult.getFamilyMap(ARCH);
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String archCores = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					osys.incrementCoreCount(archCores, (int)count);
				}
				
				nm = osResult.getFamilyMap(MODULE_WITH_VERSION);
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String moduleVersion = new String(entry.getKey());
					String[] splits = moduleVersion.split(MODULE_INFO_DELIMITER);
					long count = Bytes.toLong(entry.getValue());
				
					if (splits.length == 2) {
						osys.incrementModuleCount(splits[0], splits[1], (int)count);
					} else {
						osys.incrementModuleCount(moduleVersion, "", (int)count);
					}
				}
				
				nm = osResult.getFamilyMap(ADDON_WITH_VERSION);
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String addonVersion = new String(entry.getKey());
					String[] splits = addonVersion.split(MODULE_INFO_DELIMITER);
					long count = Bytes.toLong(entry.getValue());
					
					if (splits.length == 2) {
						osys.incrementAddonCount(splits[0], splits[1], (int)count);
					} else {
						osys.incrementAddonCount(addonVersion, "", (int)count);
					}
				}
				
				report.setOs(osys);
			} else {
				LOG.warn("OS result was empty for params: " + String.format("%s, %s, %s, %s", date, product, version, os));
			}
		} finally {
			if (table != null) {
				pool.putTable(table);
			}
		}
		
		// calculate module ratios for proper sorting
		report.calculateModuleRatios();
		
		return report;
	}

}
