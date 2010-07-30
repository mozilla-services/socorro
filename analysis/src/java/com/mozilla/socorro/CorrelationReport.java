package com.mozilla.socorro;

import gnu.trove.TObjectIntHashMap;
import gnu.trove.TObjectIntIterator;

public class CorrelationReport {
	
	private String product;
	private String version;
	private String os;
	private String signature;

	private TObjectIntHashMap<String> archCoreCounts = new TObjectIntHashMap<String>();
	private TObjectIntHashMap<String> moduleCounts = new TObjectIntHashMap<String>();
	private TObjectIntHashMap<String> moduleVersionCounts = new TObjectIntHashMap<String>();
	private TObjectIntHashMap<String> addonCounts = new TObjectIntHashMap<String>();
	private TObjectIntHashMap<String> addonVersionCounts = new TObjectIntHashMap<String>();
	
	public CorrelationReport(String product, String version, String os, String signature) {
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
	
	public TObjectIntIterator<String> getCoreCountsIterator() {
		return archCoreCounts.iterator();
	}
	
	public void coreCountAdjustOrPut(String archCores, int count) {
		archCoreCounts.adjustOrPutValue(archCores, count, count);
	}
	
	public TObjectIntIterator<String> getModuleCountsIterator() {
		return moduleCounts.iterator();
	}
	
	public void moduleAdjustOrPut(String module, int count) {
		moduleCounts.adjustOrPutValue(module, count, count);
	}
	
	public TObjectIntIterator<String> getModuleVersionCountsIterator() {
		return moduleVersionCounts.iterator();
	}
	
	public void moduleVersionAdjustOrPut(String moduleVersion, int count) {
		moduleVersionCounts.adjustOrPutValue(moduleVersion, count, count);
	}
	
	public TObjectIntIterator<String> getAddonCountsIterator() {
		return addonCounts.iterator();
	}
	
	public void addonAdjustOrPut(String addon, int count) {
		addonCounts.adjustOrPutValue(addon, count, count);
	}
	
	public TObjectIntIterator<String> getAddonVersionCountsIterator() {
		return addonVersionCounts.iterator();
	}
	
	public void addonVersionAdjustOrPut(String addonVersion, int count) {
		addonVersionCounts.adjustOrPutValue(addonVersion, count, count);
	}
	
}
