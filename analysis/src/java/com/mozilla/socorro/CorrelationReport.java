package com.mozilla.socorro;

import gnu.trove.TObjectIntHashMap;

public class CorrelationReport {
	
	private String product;
	private String version;
	private String os;
	private String signature;

	private TObjectIntHashMap<String> archCoreCounts = new TObjectIntHashMap<String>();
	private TObjectIntHashMap<String> moduleVersionCounts = new TObjectIntHashMap<String>();
	private TObjectIntHashMap<String> addonVersionCounts = new TObjectIntHashMap<String>();
	
	public CorrelationReport() {	
	}
	
	public CorrelationReport(String product, String version, String os, String signature) {
		super();
		this.product = product;
		this.version = version;
		this.os = os;
		this.signature = signature;
	}
	
	public String getProduct() {
		return product;
	}
	
	public void setProduct(String product) {
		this.product = product;
	}
	
	public String getVersion() {
		return version;
	}
	
	public void setVersion(String version) {
		this.version = version;
	}
	
	public String getOs() {
		return os;
	}
	
	public void setOs(String os) {
		this.os = os;
	}
	
	public String getSignature() {
		return signature;
	}
	
	public void setSignature(String signature) {
		this.signature = signature;
	}
	
	public void coreCountAdjustOrPut(String archCores, int count) {
		archCoreCounts.adjustOrPutValue(archCores, count, count);
	}
	
	public void moduleVersionAdjustOrPut(String moduleVersion, int count) {
		moduleVersionCounts.adjustOrPutValue(moduleVersion, count, count);
	}
	
	public void addonVersionAdjustOrPut(String moduleVersion, int count) {
		addonVersionCounts.adjustOrPutValue(moduleVersion, count, count);
	}
}
