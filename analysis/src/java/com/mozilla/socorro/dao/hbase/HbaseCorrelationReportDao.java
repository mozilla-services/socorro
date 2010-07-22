package com.mozilla.socorro.dao.hbase;

import java.io.IOException;

import org.apache.hadoop.hbase.HBaseConfiguration;
import org.apache.hadoop.hbase.client.Get;
import org.apache.hadoop.hbase.client.HTable;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.client.ResultScanner;
import org.apache.hadoop.hbase.client.Scan;

import com.mozilla.socorro.CorrelationReport;
import com.mozilla.socorro.dao.CorrelationReportDao;

public class HbaseCorrelationReportDao implements CorrelationReportDao {

	private static final String TABLE_NAME = "correlation_reports";
	
	private final HTable table;
	
	public HbaseCorrelationReportDao() throws IOException {
		HBaseConfiguration hbaseConfig = new HBaseConfiguration();
		table = new HTable(hbaseConfig, TABLE_NAME);
	}

	public CorrelationReport getReport(String product, String version, String os, String signature) throws IOException {
		CorrelationReport report = new CorrelationReport(product, version, os, signature);
		
		Scan scan = new Scan();
		scan.addColumn("count".getBytes());
		ResultScanner scanner = null;
		try {
			scanner = table.getScanner(scan);
			for (Result r : scanner) {
				r.getValue("family".getBytes(), "qualifier".getBytes());
				//report.coreCountAdjustOrPut(archCores, count);
				//report.moduleVersionAdjustOrPut(moduleVersion, count);
			}
		} finally {
			if (scanner != null) {
				scanner.close();
			}
		}
		
		return report;
	}
	
	
}
