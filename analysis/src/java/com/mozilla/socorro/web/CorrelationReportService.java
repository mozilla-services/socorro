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

package com.mozilla.socorro.web;

import gnu.trove.TObjectIntIterator;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.StringWriter;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Map;
import java.util.regex.Pattern;

import javax.servlet.http.HttpServletRequest;
import javax.ws.rs.Consumes;
import javax.ws.rs.GET;
import javax.ws.rs.POST;
import javax.ws.rs.Path;
import javax.ws.rs.PathParam;
import javax.ws.rs.core.Context;
import javax.ws.rs.core.MediaType;

import org.codehaus.jackson.JsonFactory;
import org.codehaus.jackson.JsonGenerator;
import org.codehaus.jackson.map.ObjectMapper;
import org.codehaus.jackson.type.TypeReference;

import com.google.inject.Inject;
import com.mozilla.socorro.CorrelationReport;
import com.mozilla.socorro.dao.CrashCountDao;

@Path("/correlation-report")
public class CorrelationReportService {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(CorrelationReportService.class);
	
	private static final Pattern VERSION_DELIMITER = Pattern.compile("\u0002");
	private static final SimpleDateFormat SDF = new SimpleDateFormat("yyyyMMdd");
	private static final ObjectMapper JSON_MAPPER = new ObjectMapper();
	
	private final CrashCountDao ccDao;
	
	@Inject
	public CorrelationReportService(CrashCountDao ccDao) {
		this.ccDao = ccDao;
	}
	
	private String getReportJSON(CorrelationReport report) throws IOException {
		StringWriter sw = new StringWriter();
		JsonFactory f = new JsonFactory();
		JsonGenerator g = f.createJsonGenerator(sw);

		g.writeStartObject();
		g.writeStringField("product", report.getProduct());
		g.writeStringField("version", report.getVersion());
		g.writeStringField("os", report.getOs());
		g.writeStringField("signature", report.getSignature());
		
		g.writeArrayFieldStart("core-counts");
		TObjectIntIterator<String> iter = report.getCoreCountsIterator();
		while (iter.hasNext()) {
			iter.advance();
			g.writeStartObject();
			g.writeStringField("arch", iter.key());
			
			int totalSigCoreCount = report.getTotalSigCoreCount();
			float sigRatio = totalSigCoreCount > 0 ? (float)iter.value() / (float)totalSigCoreCount : 0.0f;
			
			int osArchCoreCount = report.getOsCoreCounts().get(iter.key());
			int totalOsCoreCount = report.getTotalOsCoreCount();
			float osRatio = totalOsCoreCount > 0 ? (float)osArchCoreCount / (float)totalOsCoreCount : 0.0f;

			g.writeNumberField("sigCount", iter.value());
			g.writeNumberField("totalSigCount", totalSigCoreCount);
			g.writeNumberField("sigPercent", sigRatio * 100.0f);
			
			g.writeNumberField("osCount", osArchCoreCount);
			g.writeNumberField("totalOsCount", totalOsCoreCount);
			g.writeNumberField("osPercent", osRatio * 100.0f);

			g.writeEndObject();
		}
		g.writeEndArray();
		
		g.writeArrayFieldStart("interesting-modules");
		iter = report.getModuleCountsIterator();
		while (iter.hasNext()) {
			iter.advance();
			g.writeStartObject();
			g.writeStringField("module", iter.key());
			
			int totalSigModuleCount = report.getTotalSigModuleCount();
			float sigRatio = totalSigModuleCount > 0 ? (float)iter.value() / (float)totalSigModuleCount : 0.0f;
			
			int osModuleCount = report.getOsModuleCounts().get(iter.key());
			int totalOsModuleCount = report.getTotalOsModuleCount();
			float osRatio = totalOsModuleCount > 0 ? (float)osModuleCount / (float)totalOsModuleCount : 0.0f;
			
			g.writeNumberField("sigCount", iter.value());
			g.writeNumberField("totalSigCount", totalSigModuleCount);
			g.writeNumberField("sigPercent", sigRatio * 100.0f);
			
			g.writeNumberField("osCount", osModuleCount);
			g.writeNumberField("totalOsCount", totalOsModuleCount);
			g.writeNumberField("osPercent", osRatio * 100.0f);
			
			g.writeEndObject();
		}
		g.writeEndArray();
		
		g.writeArrayFieldStart("interesting-modules-with-versions");
		iter = report.getModuleVersionCountsIterator();
		while (iter.hasNext()) {
			iter.advance();
			g.writeStartObject();
			String[] splits = VERSION_DELIMITER.split(iter.key());
			g.writeStringField("module", splits[0]);
			if (splits.length == 2) {
				g.writeStringField("version", splits[1]);
			} else {
				g.writeStringField("version", "unknown");
			}
			int totalSigModuleVersionCount = report.getTotalSigModuleVersionCount();
			float sigRatio = totalSigModuleVersionCount > 0 ? (float)iter.value() / (float)totalSigModuleVersionCount : 0.0f;
			
			int osModuleVersionCount = report.getOsModuleVersionCounts().get(iter.key());
			int totalOsModuleVersionCount = report.getTotalOsModuleVersionCount();
			float osRatio = totalOsModuleVersionCount > 0 ? (float)osModuleVersionCount / (float)totalOsModuleVersionCount : 0.0f;
			
			g.writeNumberField("sigCount", iter.value());
			g.writeNumberField("totalSigCount", totalSigModuleVersionCount);
			g.writeNumberField("sigPercent", sigRatio * 100.0f);
			
			g.writeNumberField("osCount", osModuleVersionCount);
			g.writeNumberField("totalOsCount", totalOsModuleVersionCount);
			g.writeNumberField("osPercent", osRatio * 100.0f);
			
			g.writeEndObject();
		}
		g.writeEndArray();
		
		g.writeArrayFieldStart("interesting-addons");
		iter = report.getAddonCountsIterator();
		while (iter.hasNext()) {
			iter.advance();
			g.writeStartObject();
			g.writeStringField("addon", iter.key());
			
			int totalSigAddonCount = report.getTotalSigAddonCount();
			float sigRatio = totalSigAddonCount > 0 ? (float)iter.value() / (float)totalSigAddonCount : 0.0f;
			
			int osAddonCount = report.getOsAddonCounts().get(iter.key());
			int totalOsAddonCount = report.getTotalOsAddonCount();
			float osRatio = totalOsAddonCount > 0 ? (float)osAddonCount / (float)totalOsAddonCount : 0.0f;
			
			g.writeNumberField("sigCount", iter.value());
			g.writeNumberField("totalSigCount", totalSigAddonCount);
			g.writeNumberField("sigPercent", sigRatio * 100.0f);
			
			g.writeNumberField("osCount", osAddonCount);
			g.writeNumberField("totalOsCount", totalOsAddonCount);
			g.writeNumberField("osPercent", osRatio * 100.0f);
			
			g.writeEndObject();
		}
		g.writeEndArray();
		
		g.writeArrayFieldStart("interesting-addons-with-versions");
		iter = report.getAddonVersionCountsIterator();
		while (iter.hasNext()) {
			iter.advance();
			g.writeStartObject();
			String[] splits = VERSION_DELIMITER.split(iter.key());
			g.writeStringField("addon", splits[0]);
			if (splits.length == 2) {
				g.writeStringField("version", splits[1]);
			} else {
				g.writeStringField("version", "unknown");
			}
			
			int totalSigAddonVersionCount = report.getTotalSigAddonVersionCount();
			float sigRatio = totalSigAddonVersionCount > 0 ? (float)iter.value() / (float)totalSigAddonVersionCount : 0.0f;
			
			int osAddonVersionCount = report.getOsAddonVersionCounts().get(iter.key());
			int totalOsAddonVersionCount = report.getTotalOsAddonVersionCount();
			float osRatio = totalOsAddonVersionCount > 0 ? (float)osAddonVersionCount / (float)totalOsAddonVersionCount : 0.0f;
			
			g.writeNumberField("sigCount", iter.value());
			g.writeNumberField("totalSigCount", totalSigAddonVersionCount);
			g.writeNumberField("sigPercent", sigRatio * 100.0f);
			
			g.writeNumberField("osCount", osAddonVersionCount);
			g.writeNumberField("totalOsCount", totalOsAddonVersionCount);
			g.writeNumberField("osPercent", osRatio * 100.0f);
			
			g.writeEndObject();
		}
		g.writeEndArray();

		g.writeEndObject();
		g.close();
		
		return sw.toString();
	}
	
	@GET
	@Path("report/{date}/{product}/{version}/{os}/{signature}")
	public String getReport(@PathParam("date") String date, @PathParam("product") String product, @PathParam("version") String version, 
							@PathParam("os") String os, @PathParam("signature") String signature) {
		StringBuilder sb = new StringBuilder();
		try {
			CorrelationReport report = ccDao.getReport(SDF.parse(date), product, version, os, signature);
			sb.append(getReportJSON(report));
		} catch (IOException e) {
			LOG.error("Problem getting or serializing report", e);
		} catch (ParseException e) {
			LOG.error("Problem parsing date", e);
		}
		
		return sb.toString();
	}
	
	@SuppressWarnings("unchecked")
	@POST
	@Consumes(MediaType.APPLICATION_JSON)
	@Path("increment-count/{date}/{product}/{version}/{os}/{signature}")
	public void incrementCounts(@PathParam("date") String date, @PathParam("product") String product, @PathParam("version") String version, 
								@PathParam("os") String os, @PathParam("signature") String signature, @Context HttpServletRequest request) {
		BufferedReader reader = null;
		try {
			// This is an untyped parse so the caller is expected to know the types
			Map<String,Object> archModuleMap = JSON_MAPPER.readValue(request.getInputStream(), new TypeReference<Map<String,Object>>() { });
			String arch = (String)archModuleMap.get("arch");
			Map<String,String> moduleVersions = (Map<String,String>)archModuleMap.get("module-version");
			Map<String,String> addonVersions = (Map<String,String>)archModuleMap.get("addon-version");

			ccDao.incrementCounts(SDF.parse(date), product, version, os, signature, arch, moduleVersions, addonVersions);
		} catch (IOException e) {
			LOG.error("Problem getting or serializing report", e);
		} catch (ParseException e) {
			LOG.error("Problem parsing date", e);
		} finally {
			if (reader != null) {
				try {
					reader.close();
				} catch (IOException e) {
					LOG.error("Problem closing reader", e);
				}
			}
		}
	}
}
