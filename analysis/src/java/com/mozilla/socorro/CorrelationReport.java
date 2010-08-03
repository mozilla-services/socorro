/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Mozilla Socorro.
 *
 * The Initial Developer of the Original Code is the Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2010
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 * 
 *   Xavier Stevens <xstevens@mozilla.com>, Mozilla Corporation (original author)
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

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
	
	private int totalSigCoreCount = 0;
	private int totalSigModuleCount = 0;
	private int totalSigModuleVersionCount = 0;
	private int totalSigAddonCount = 0;
	private int totalSigAddonVersionCount = 0;
	
	private TObjectIntHashMap<String> osArchCoreCounts = new TObjectIntHashMap<String>();
	private TObjectIntHashMap<String> osModuleCounts = new TObjectIntHashMap<String>();
	private TObjectIntHashMap<String> osModuleVersionCounts = new TObjectIntHashMap<String>();
	private TObjectIntHashMap<String> osAddonCounts = new TObjectIntHashMap<String>();
	private TObjectIntHashMap<String> osAddonVersionCounts = new TObjectIntHashMap<String>();
	
	private int totalOsCoreCount = 0;
	private int totalOsModuleCount = 0;
	private int totalOsModuleVersionCount = 0;
	private int totalOsAddonCount = 0;
	private int totalOsAddonVersionCount = 0;
	
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
	
	public TObjectIntHashMap<String> getCoreCoreCounts() {
		return archCoreCounts;
	}
	
	public TObjectIntIterator<String> getCoreCountsIterator() {
		return archCoreCounts.iterator();
	}
	
	public void coreCountAdjustOrPut(String archCores, int count) {
		archCoreCounts.adjustOrPutValue(archCores, count, count);
		totalSigCoreCount += count;
	}
	
	public TObjectIntIterator<String> getModuleCountsIterator() {
		return moduleCounts.iterator();
	}
	
	public TObjectIntHashMap<String> getModuleCounts() {
		return moduleCounts;
	}
	
	public void moduleAdjustOrPut(String module, int count) {
		moduleCounts.adjustOrPutValue(module, count, count);
		totalSigModuleCount += count;
	}
	
	public TObjectIntHashMap<String> getModuleVersionCounts() {
		return moduleVersionCounts;
	}
	
	public TObjectIntIterator<String> getModuleVersionCountsIterator() {
		return moduleVersionCounts.iterator();
	}
	
	public void moduleVersionAdjustOrPut(String moduleVersion, int count) {
		moduleVersionCounts.adjustOrPutValue(moduleVersion, count, count);
		totalSigModuleVersionCount += count;
	}
	
	public TObjectIntHashMap<String> getAddonCounts() {
		return addonCounts;
	}
	
	public TObjectIntIterator<String> getAddonCountsIterator() {
		return addonCounts.iterator();
	}
	
	public void addonAdjustOrPut(String addon, int count) {
		addonCounts.adjustOrPutValue(addon, count, count);
		totalSigAddonCount += count;
	}
	
	public TObjectIntHashMap<String> getAddonVersionCounts() {
		return addonVersionCounts;
	}
	
	public TObjectIntIterator<String> getAddonVersionCountsIterator() {
		return addonVersionCounts.iterator();
	}
	
	public void addonVersionAdjustOrPut(String addonVersion, int count) {
		addonVersionCounts.adjustOrPutValue(addonVersion, count, count);
		totalSigAddonVersionCount += count;
	}

	public TObjectIntHashMap<String> getOsCoreCounts() {
		return osArchCoreCounts;
	}

	public TObjectIntIterator<String> getOsCoreCountsIterator() {
		return osArchCoreCounts.iterator();
	}
	
	public void osCoreCountAdjustOrPut(String archCores, int count) {
		osArchCoreCounts.adjustOrPutValue(archCores, count, count);
		totalOsCoreCount += count;
	}
	
	public TObjectIntHashMap<String> getOsModuleCounts() {
		return osModuleCounts;
	}

	public void osModuleCountAdjustOrPut(String module, int count) {
		osModuleCounts.adjustOrPutValue(module, count, count);
		totalOsModuleCount += count;
	}
	
	public TObjectIntHashMap<String> getOsModuleVersionCounts() {
		return osModuleVersionCounts;
	}

	public void osModuleVersionCountAdjustOrPut(String moduleVersion, int count) {
		osModuleVersionCounts.adjustOrPutValue(moduleVersion, count, count);
		totalOsModuleVersionCount += count;
	}
	
	public TObjectIntHashMap<String> getOsAddonCounts() {
		return osAddonCounts;
	}
	
	public void osAddonCountAdjustOrPut(String addon, int count) {
		osAddonCounts.adjustOrPutValue(addon, count, count);
		totalOsAddonCount += count;
	}

	public TObjectIntHashMap<String> getOsAddonVersionCounts() {
		return osAddonVersionCounts;
	}
	
	public void osAddonVersionCountAdjustOrPut(String addonVersion, int count) {
		osAddonVersionCounts.adjustOrPutValue(addonVersion, count, count);
		totalOsAddonVersionCount += count;
	}
	
	public int getTotalSigCoreCount() {
		return totalSigCoreCount;
	}

	public int getTotalOsCoreCount() {
		return totalOsCoreCount;
	}
	
	public int getTotalSigModuleCount() {
		return totalSigModuleCount;
	}

	public int getTotalSigModuleVersionCount() {
		return totalSigModuleVersionCount;
	}

	public int getTotalSigAddonCount() {
		return totalSigAddonCount;
	}

	public int getTotalSigAddonVersionCount() {
		return totalSigAddonVersionCount;
	}

	public int getTotalOsModuleCount() {
		return totalOsModuleCount;
	}

	public int getTotalOsModuleVersionCount() {
		return totalOsModuleVersionCount;
	}

	public int getTotalOsAddonCount() {
		return totalOsAddonCount;
	}

	public int getTotalOsAddonVersionCount() {
		return totalOsAddonVersionCount;
	}

}
