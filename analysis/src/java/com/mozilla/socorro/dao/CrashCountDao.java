package com.mozilla.socorro.dao;

import java.io.IOException;
import java.util.Date;
import java.util.Map;

import com.mozilla.socorro.CorrelationReport;

public interface CrashCountDao {

	public void incrementCounts(Date date, String product, String version, String os, String signature, String arch, Map<String,String> moduleVersions, Map<String,String> addonVersions) throws IOException;
	
	public CorrelationReport getReport(Date date, String product, String version, String os, String signature) throws IOException;
	
}
