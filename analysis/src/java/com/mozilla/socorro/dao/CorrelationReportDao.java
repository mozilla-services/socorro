package com.mozilla.socorro.dao;

import java.io.IOException;

import com.mozilla.socorro.CorrelationReport;

public interface CorrelationReportDao {

	public CorrelationReport getReport(String product, String version, String os, String signature) throws IOException;
	
}
