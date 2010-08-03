/**
 * Copyright 2007 The Apache Software Foundation
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.hadoop.hbase.mapreduce;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.hbase.client.Scan;
import org.apache.hadoop.hbase.util.Base64;
import org.apache.hadoop.io.ArrayWritable;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.io.WritableComparable;
import org.apache.hadoop.mapreduce.Job;

public class MultiScanTableMapReduceUtil {

	private static Log LOG = LogFactory.getLog(MultiScanTableMapReduceUtil.class);

	/**
	 * Use this before submitting a TableMap job. It will appropriately set up
	 * the job.
	 * 
	 * @param table
	 *            The table name to read from.
	 * @param scans
	 *            The scan instances with the columns, time range etc.
	 * @param mapper
	 *            The mapper class to use.
	 * @param outputKeyClass
	 *            The class of the output key.
	 * @param outputValueClass
	 *            The class of the output value.
	 * @param job
	 *            The current job to adjust.
	 * @throws IOException
	 *             When setting up the details fails.
	 */
	@SuppressWarnings("unchecked")
	public static void initMultiScanTableMapperJob(final String table, final Scan[] scans,
			final Class<? extends TableMapper> mapper, final Class<? extends WritableComparable> outputKeyClass,
			final Class<? extends Writable> outputValueClass, final Job job) throws IOException {
		
		job.setInputFormatClass(MultiScanTableInputFormat.class);
	    if (outputValueClass != null) {
	    	job.setMapOutputValueClass(outputValueClass);
	    }
	    if (outputKeyClass != null) {
	    	job.setMapOutputKeyClass(outputKeyClass);
	    }
	    job.setMapperClass(mapper);
		job.getConfiguration().set(MultiScanTableInputFormat.INPUT_TABLE, table);
		job.getConfiguration().set(MultiScanTableInputFormat.SCANS, convertScanArrayToString(scans));
	}

	/**
	 * Converts base64 scans string back into a Scan array
	 * @param base64
	 * @return
	 * @throws IOException
	 */
	public static Scan[] convertStringToScanArray(final String base64) throws IOException {
		final DataInputStream dis = new DataInputStream(new ByteArrayInputStream(Base64.decode(base64)));

		ArrayWritable aw = new ArrayWritable(Scan.class);
		aw.readFields(dis);
		
		Writable[] writables = aw.get();
		Scan[] scans = new Scan[writables.length];
		for (int i=0; i < writables.length; i++) {
			scans[i] = (Scan)writables[i];
		}

		return scans;
	}

	/**
	 * Converts an array of Scan objects into a base64 string
	 * @param scans
	 * @return
	 * @throws IOException
	 */
	public static String convertScanArrayToString(final Scan[] scans) throws IOException {
		final ByteArrayOutputStream baos = new ByteArrayOutputStream();
		final DataOutputStream dos = new DataOutputStream(baos);

		ArrayWritable aw = new ArrayWritable(Scan.class, scans);
		aw.write(dos);

		return Base64.encodeBytes(baos.toByteArray());
	}

}
