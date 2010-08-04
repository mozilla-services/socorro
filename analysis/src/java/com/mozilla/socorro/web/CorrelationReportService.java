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

import gnu.trove.TObjectIntHashMap;
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
import javax.ws.rs.WebApplicationException;
import javax.ws.rs.core.Context;
import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.Response;

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
	
	private void generateJSONArray(JsonGenerator g, String arrayName, String fieldName, TObjectIntIterator<String> iter, int totalSigCount, TObjectIntHashMap<String> osCountsMap, int totalOsCount, boolean withVersions) throws IOException {
		g.writeArrayFieldStart(arrayName);
		while (iter.hasNext()) {
			iter.advance();
			g.writeStartObject();
			if (!withVersions) {
				g.writeStringField(fieldName, iter.key());
			} else {
				String[] splits = VERSION_DELIMITER.split(iter.key());
				g.writeStringField(fieldName, splits[0]);
				if (splits.length == 2) {
					g.writeStringField("version", splits[1]);
				} else {
					g.writeStringField("version", "unknown");
				}
			}

			float sigRatio = totalSigCount > 0 ? (float)iter.value() / (float)totalSigCount : 0.0f;
			int osCount = osCountsMap.get(iter.key());
			float osRatio = totalOsCount > 0 ? (float)osCount / (float)totalOsCount : 0.0f;
			
			g.writeNumberField("sigCount", iter.value());
			g.writeNumberField("totalSigCount", totalSigCount);
			g.writeNumberField("sigPercent", sigRatio * 100.0f);
			
			g.writeNumberField("osCount", osCount);
			g.writeNumberField("totalOsCount", totalOsCount);
			g.writeNumberField("osPercent", osRatio * 100.0f);
			
			g.writeEndObject();
		}
		g.writeEndArray();
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
		
		generateJSONArray(g, "core-counts", "arch", report.getCoreCountsIterator(), report.getTotalSigCoreCount(), 
						  report.getOsCoreCounts(), report.getTotalOsCoreCount(), false);
		generateJSONArray(g, "interesting-modules", "module", report.getModuleCountsIterator(), 
						  report.getTotalSigModuleCount(), report.getOsModuleCounts(), report.getTotalOsModuleCount(), false);
		generateJSONArray(g, "interesting-modules-with-versions", "module", report.getModuleVersionCountsIterator(), 
						  report.getTotalSigModuleVersionCount(), report.getOsModuleVersionCounts(), report.getTotalOsModuleVersionCount(), true);
		generateJSONArray(g, "interesting-addons", "addon", report.getAddonCountsIterator(), report.getTotalSigAddonCount(), 
						  report.getOsAddonCounts(), report.getTotalOsAddonCount(), false);
		generateJSONArray(g, "interesting-addons-with-versions", "addon", report.getAddonVersionCountsIterator(), 
				  report.getTotalSigAddonVersionCount(), report.getOsAddonVersionCounts(), report.getTotalOsAddonVersionCount(), true);

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
			throw new WebApplicationException(e, Response.Status.INTERNAL_SERVER_ERROR);
		} catch (ParseException e) {
			LOG.error("Problem parsing date", e);
			throw new WebApplicationException(e, Response.Status.INTERNAL_SERVER_ERROR);
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
			throw new WebApplicationException(e, Response.Status.INTERNAL_SERVER_ERROR);
		} catch (ParseException e) {
			LOG.error("Problem parsing date", e);
			throw new WebApplicationException(e, Response.Status.INTERNAL_SERVER_ERROR);
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
