/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package com.mozilla.socorro.hadoop;

import java.io.BufferedWriter;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.HashMap;
import java.util.Map;

import org.apache.commons.lang.StringUtils;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.hbase.HBaseConfiguration;
import org.apache.hadoop.hbase.client.HTable;
import org.apache.hadoop.hbase.client.Result;
import org.apache.hadoop.hbase.client.ResultScanner;
import org.apache.hadoop.hbase.client.Scan;
import org.apache.hadoop.hbase.filter.KeyOnlyFilter;

import com.mozilla.hadoop.hbase.mapreduce.MultiScanTableMapReduceUtil;

public class KeysForDateRange {

    public static void main(String[] args) throws ParseException {
        String startDateStr = args[0];
        String endDateStr = args[1];
        String outputPath = args[2];

        Calendar startCal = Calendar.getInstance();
        Calendar endCal = Calendar.getInstance();

        SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMdd");
        if (!StringUtils.isBlank(startDateStr)) {
            startCal.setTime(sdf.parse(startDateStr));
        }
        if (!StringUtils.isBlank(endDateStr)) {
            endCal.setTime(sdf.parse(endDateStr));
        }

        Configuration hbaseConf = HBaseConfiguration.create();
        HTable table = null;
        Map<byte[], byte[]> columns = new HashMap<byte[],byte[]>();
        columns.put("processed_data".getBytes(), "json".getBytes());
        Scan[] scans = MultiScanTableMapReduceUtil.generateHexPrefixScans(startCal, endCal, "yyMMdd", columns, 100, false);
        ResultScanner scanner = null;
        BufferedWriter writer = null;
        try {
            writer = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(outputPath), "UTF-8"));
            table = new HTable(hbaseConf, "crash_reports");
            for (Scan s : scans) {
                // Add key-only filter for speed
                s.setFilter(new KeyOnlyFilter());

                System.out.println("Processing scan range: " + new String(s.getStartRow()) + " - " + new String(s.getStopRow()));
                scanner = table.getScanner(s);
                Result r = null;
                while ((r = scanner.next()) != null) {
                   writer.write(new String(r.getRow()));
                   writer.newLine();
                }
                scanner.close();
            }
        } catch (IOException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        } finally {
            if (writer != null) {
                try {
                    writer.close();
                } catch (IOException e) {
                    // TODO Auto-generated catch block
                    e.printStackTrace();
                }
            }
            if (scanner != null) {
                scanner.close();
            }
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
