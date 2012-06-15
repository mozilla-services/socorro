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

import java.util.Map;

public class CorrelationReport {

	private String product = null;
	private String productVersion = null;
	private OperatingSystem os = null;

	public CorrelationReport(String product, String productVersion, String os) {
		this.product = product;
		this.productVersion = productVersion;
		this.os = new OperatingSystem(os);
	}

	public CorrelationReport(String product, String productVersion, String os, String signature) {
		this(product, productVersion, os);
		this.os.addSignature(signature, new Signature(signature));
	}

	public String getProduct() {
		return product;
	}

	public void setProduct(String product) {
		this.product = product;
	}

	public String getProductVersion() {
		return productVersion;
	}

	public void setProductVersion(String productVersion) {
		this.productVersion = productVersion;
	}

	public OperatingSystem getOs() {
		return os;
	}

	public void setOs(OperatingSystem os) {
		this.os = os;
	}

	public void calculateModuleRatios() {
		Map<String, Signature> signatures = os.getSignatures();
		Map<String, Module> osModuleMap = os.getModuleCounts();
		Map<String, Module> osAddonMap = os.getAddonCounts();
		for (Map.Entry<String, Signature> sigEntry : signatures.entrySet()) {
			Signature sig = sigEntry.getValue();

			Map<String, Module> modules = sig.getModuleCounts();
			for (Map.Entry<String, Module> moduleEntry : modules.entrySet()) {
				Module m = moduleEntry.getValue();
				float sigRatio = sig.getCount() > 0 ? (float)m.getCount() / (float)sig.getCount() : 0.0f;
				int osCount = osModuleMap.get(moduleEntry.getKey()).getCount();
				float osRatio = os.getCount() > 0 ? (float)osCount / (float)os.getCount() : 0.0f;

				m.setSigRatio(sigRatio);
				m.setOsRatio(osRatio);

				modules.put(moduleEntry.getKey(), m);
			}
			sig.setModuleCounts(modules);

			Map<String, Module> addons = sig.getAddonCounts();
			for (Map.Entry<String, Module> addonEntry : addons.entrySet()) {
				Module m = addonEntry.getValue();
				float sigRatio = sig.getCount() > 0 ? (float)m.getCount() / (float)sig.getCount() : 0.0f;
				int osCount = osAddonMap.get(addonEntry.getKey()).getCount();
				float osRatio = os.getCount() > 0 ? (float)osCount / (float)os.getCount() : 0.0f;

				m.setSigRatio(sigRatio);
				m.setOsRatio(osRatio);

				addons.put(addonEntry.getKey(), m);
			}
			sig.setAddonCounts(addons);

			signatures.put(sigEntry.getKey(), sig);
		}

		os.setSignatures(signatures);
	}
}
