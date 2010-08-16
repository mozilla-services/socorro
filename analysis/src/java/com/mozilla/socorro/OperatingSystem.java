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

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.mozilla.util.MapValueComparator;

public class OperatingSystem {
	
	private String name = null;
	private int count = 0;
	private Map<String, Signature> signatures = new HashMap<String, Signature>();
	private Map<String, Integer> coreCounts = new HashMap<String, Integer>();
	private Map<String, Module> moduleCounts = new HashMap<String, Module>();
	private Map<String, Module> addonCounts = new HashMap<String, Module>();
	
	public OperatingSystem(String name) {
		this.name = name;
	}
	
	public String getName() {
		return name;
	}
	
	public int getCount() {
		return count;
	}

	public void setCount(int count) {
		this.count = count;
	}
	
	public Map<String, Signature> getSignatures() {
		return signatures;
	}
	
	public void addSignature(String name, Signature signature) {
		this.signatures.put(name, signature);
	}
	
	public void setSignatures(Map<String, Signature> signatures) {
		this.signatures = signatures;
	}
	
	public Map<String, Integer> getCoreCounts() {
		return coreCounts;
	}
	
	public List<Map.Entry<String, Integer>> getSortedCoreCounts() {
		List<Map.Entry<String, Integer>> coreCountPairs = new ArrayList<Map.Entry<String,Integer>>(coreCounts.entrySet());
		Collections.sort(coreCountPairs, Collections.reverseOrder(new MapValueComparator()));
		return coreCountPairs;
	}
	
	public void incrementCoreCount(String arch, int count) {
		int existingCount = 0;
		if (coreCounts.containsKey(arch)) {
			existingCount = coreCounts.get(arch);
		}
		coreCounts.put(arch, existingCount + count);
	}
	
	public void setCoreCounts(Map<String, Integer> coreCounts) {
		this.coreCounts = coreCounts;
	}
	
	public Map<String, Module> getModuleCounts() {
		return moduleCounts;
	}
	
	public List<Module> getSortedModuleCounts() {
		List<Module> modules = new ArrayList<Module>(moduleCounts.values());
		Collections.sort(modules, Collections.reverseOrder(new Module.ModuleComparator()));
		return modules;
	}
	
	public void incrementModuleCount(String moduleName, String moduleVersion, int count) {
		Module module = null;
		if (moduleCounts.containsKey(moduleName)) {
			module = moduleCounts.get(moduleName);
		} else {
			module = new Module(moduleName);
		}
		module.setCount(module.getCount() + count);
		module.incrementVersionCount(moduleVersion, count);
		moduleCounts.put(moduleName, module);
	}
	
	public void setModuleCounts(Map<String, Module> moduleCounts) {
		this.moduleCounts = moduleCounts;
	}
	
	public Map<String, Module> getAddonCounts() {
		return addonCounts;
	}
	
	public List<Module> getSortedAddonCounts() {
		List<Module> addons = new ArrayList<Module>(addonCounts.values());
		Collections.sort(addons, Collections.reverseOrder(new Module.ModuleComparator()));
		return addons;
	}
	
	public void incrementAddonCount(String addonName, String addonVersion, int count) {
		Module module = null;
		if (addonCounts.containsKey(addonName)) {
			module = addonCounts.get(addonName);
		} else {
			module = new Module(addonName);
		}
		module.setCount(module.getCount() + count);
		module.incrementVersionCount(addonVersion, count);
		addonCounts.put(addonName, module);
	}
	
	public void setAddonCounts(Map<String, Module> addonCounts) {
		this.addonCounts = addonCounts;
	}
	
}
