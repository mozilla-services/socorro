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
