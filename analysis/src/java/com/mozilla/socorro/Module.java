/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package com.mozilla.socorro;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.mozilla.util.MapValueComparator;

public class Module {

	private String name;
	private int count;
	private float sigRatio = 0.0f;
	private float osRatio = 0.0f;
	private Map<String, Integer> versionCounts = new HashMap<String, Integer>();

	public Module(String name) {
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

	public Map<String, Integer> getVersionCounts() {
		return versionCounts;
	}

	public List<Map.Entry<String, Integer>> getSortedVersionCounts() {
		List<Map.Entry<String, Integer>> versionPairs = new ArrayList<Map.Entry<String, Integer>>(versionCounts.entrySet());
		Collections.sort(versionPairs, Collections.reverseOrder(new MapValueComparator()));
		return versionPairs;
	}

	public void incrementVersionCount(String moduleVersion, int count) {
		int existingCount = 0;
		if (versionCounts.containsKey(moduleVersion)) {
			existingCount = versionCounts.get(moduleVersion);
		}
		versionCounts.put(moduleVersion, existingCount + count);
	}

	public void setVersionCounts(Map<String, Integer> versionCounts) {
		this.versionCounts = versionCounts;
	}

	public float getSigRatio() {
		return sigRatio;
	}

	public void setSigRatio(float sigRatio) {
		this.sigRatio = sigRatio;
	}

	public float getOsRatio() {
		return osRatio;
	}

	public void setOsRatio(float osRatio) {
		this.osRatio = osRatio;
	}

	public static class ModuleComparator implements Comparator<Module> {

		public int compare(Module o1, Module o2) {
			float diffRatio1 = o1.getSigRatio() - o1.getOsRatio();
			float diffRatio2 = o2.getSigRatio() - o2.getOsRatio();

			return diffRatio1 < diffRatio2 ? -1 : diffRatio1 > diffRatio2 ? 1 : 0;
		}

	}

}
