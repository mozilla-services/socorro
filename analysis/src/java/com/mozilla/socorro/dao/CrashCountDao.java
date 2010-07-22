package com.mozilla.socorro.dao;

import java.io.IOException;
import java.util.Date;

import com.mozilla.socorro.CorrelationReport;

public interface CrashCountDao {

	public CorrelationReport getReport(Date date, String product, String version, String os, String signature) throws IOException;
	
}
