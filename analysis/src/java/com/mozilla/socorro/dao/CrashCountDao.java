/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package com.mozilla.socorro.dao;

import java.io.IOException;
import java.util.Map;

import com.mozilla.socorro.CorrelationReport;

public interface CrashCountDao {

	public void incrementCounts(String date, String product, String version, String os, String signature, String arch, Map<String,String> moduleVersions, Map<String,String> addonVersions) throws IOException;

	public CorrelationReport getReport(String date, String product, String version, String os, String signature) throws IOException;

	public CorrelationReport getTopCrashers(String date, String product, String version, String os) throws IOException;

}
