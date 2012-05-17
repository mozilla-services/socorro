/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
