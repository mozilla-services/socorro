package com.mozilla.socorro.dao.hbase;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.Date;
import java.util.Map;
import java.util.NavigableMap;

import org.apache.commons.lang.StringUtils;
import org.apache.hadoop.hbase.HBaseConfiguration;
import org.apache.hadoop.hbase.client.Get;
import org.apache.hadoop.hbase.client.HTable;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.client.ResultScanner;
import org.apache.hadoop.hbase.client.Scan;
import org.apache.hadoop.hbase.util.Bytes;

import com.mozilla.socorro.CorrelationReport;
import com.mozilla.socorro.dao.CrashCountDao;

public class HbaseCrashCountDao implements CrashCountDao {

	private static final String TABLE_NAME = "correlation_reports";
	
	private final HTable table;
	
	public HbaseCrashCountDao() throws IOException {
		HBaseConfiguration hbaseConfig = new HBaseConfiguration();
		table = new HTable(hbaseConfig, TABLE_NAME);
	}

	private byte[] makeRowKey(Date date, String product, String version, String os, String signature) throws IOException {
		ByteArrayOutputStream baos = new ByteArrayOutputStream();
		baos.write(Bytes.toBytes(date.getTime()));
		baos.write(Bytes.toBytes(product));
		baos.write(Bytes.toBytes(version));
		baos.write(Bytes.toBytes(os));
		baos.write(Bytes.toBytes(signature));
		
		return baos.toByteArray();
	}
	
	public CorrelationReport getReport(Date date, String product, String version, String os, String signature) throws IOException {
		CorrelationReport report = new CorrelationReport(product, version, os, signature);
		
		Get g = new Get(makeRowKey(date, product, version, os, signature));
		Result r = table.get(g);
//		
//		String oskey = product + version + os;
//		g = new Get(Bytes.toBytes(oskey));
//		r = table.get(g);
//		r.getValue(Bytes.toBytes("count"));
		
//		Scan scan = new Scan();
//		scan.addColumn(Bytes.toBytes("product:" + product + " " + version));
//		scan.addColumn(Bytes.toBytes("product_version:" + version));
//		scan.addColumn(Bytes.toBytes("os:" + os));
//		scan.addColumn(Bytes.toBytes("signature"));
//		ResultScanner scanner = null;
//		try {
//			scanner = table.getScanner(scan);
//			for (Result r : scanner) {
		if (r != null) {
				NavigableMap<byte[],byte[]> nm = r.getFamilyMap(Bytes.toBytes("arch"));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String archCores = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					report.coreCountAdjustOrPut(archCores, (int)count);
				}
				
				nm = r.getFamilyMap(Bytes.toBytes("module"));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String moduleVersion = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					report.moduleVersionAdjustOrPut(moduleVersion, (int)count);
				}
				
				nm = r.getFamilyMap(Bytes.toBytes("addon"));
				for (Map.Entry<byte[], byte[]> entry : nm.entrySet()) {
					String addonVerison = new String(entry.getKey());
					long count = Bytes.toLong(entry.getValue());
					
					report.addonVersionAdjustOrPut(addonVerison, (int)count);
				}
		}
//			}
//		} finally {
//			if (scanner != null) {
//				scanner.close();
//			}
//		}
		
		return report;
	}
	
	
}
