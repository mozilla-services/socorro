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

import java.io.BufferedReader;
import java.io.IOException;
import java.io.StringWriter;
import java.util.List;
import java.util.Map;

import javax.servlet.http.HttpServletRequest;
import javax.ws.rs.Consumes;
import javax.ws.rs.GET;
import javax.ws.rs.POST;
import javax.ws.rs.Path;
import javax.ws.rs.PathParam;
import javax.ws.rs.Produces;
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
import com.mozilla.socorro.Module;
import com.mozilla.socorro.OperatingSystem;
import com.mozilla.socorro.Signature;
import com.mozilla.socorro.dao.CrashCountDao;

@Path("/correlation-report")
public class CorrelationReportService {

	private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(CorrelationReportService.class);
	
	private static final ObjectMapper JSON_MAPPER = new ObjectMapper();
	private static final int MIN_SIG_COUNT = 10;
	private static final float MIN_BASELINE_DIFF = 0.05f;
	
	private final CrashCountDao ccDao;
	
	@Inject
	public CorrelationReportService(CrashCountDao ccDao) {
		this.ccDao = ccDao;
	}
	
	private void generateJSONArray(JsonGenerator g, String arrayName, String fieldName, OperatingSystem os, Signature sig, boolean addons, boolean withVersions) throws IOException {
		g.writeArrayFieldStart(arrayName);
		List<Module> modules = null;
		Map<String, Module> osModuleMap = null;
		if (addons) {
			modules = sig.getSortedModuleCounts();
			osModuleMap = os.getModuleCounts();
		} else {
			modules = sig.getSortedAddonCounts();
			osModuleMap = os.getAddonCounts();
		}
		
		for (Module m : modules) {
			float sigRatio = sig.getCount() > 0 ? (float)m.getCount() / (float)sig.getCount() : 0.0f;
			int osCount = osModuleMap.get(m.getName()).getCount();
			float osRatio = os.getCount() > 0 ? (float)osCount / (float)os.getCount() : 0.0f;
			
			if ((sigRatio - osRatio) >= MIN_BASELINE_DIFF) {
				g.writeStartObject();
				g.writeStringField(fieldName, m.getName());
				g.writeNumberField("sc", m.getCount());
				g.writeNumberField("tsc", sig.getCount());
				g.writeNumberField("sp", (int)(sigRatio * 100.0f));
				g.writeNumberField("oc", osCount);
				g.writeNumberField("toc", os.getCount());
				g.writeNumberField("op", (int)(osRatio * 100.0f));
				
				g.writeArrayFieldStart("versions");
				for (Map.Entry<String, Integer> versionEntry : m.getSortedVersionCounts()) {
					float versionSigRatio = sig.getCount() > 0 ? (float)versionEntry.getValue() / (float)sig.getCount() : 0.0f;
					int versionOsCount = osModuleMap.get(m.getName()).getVersionCounts().get(versionEntry.getKey());
					float versionOsRatio = os.getCount() > 0 ? (float)osCount / (float)os.getCount() : 0.0f;
					
					g.writeStartObject();
					g.writeStringField("v", versionEntry.getKey());
					g.writeNumberField("sc", versionEntry.getValue());
					g.writeNumberField("tsc", sig.getCount());
					g.writeNumberField("sp", (int)(versionSigRatio * 100.0f));
					g.writeNumberField("oc", versionOsCount);
					g.writeNumberField("toc", os.getCount());
					g.writeNumberField("op", (int)(versionOsRatio * 100.0f));
					g.writeEndObject();
				}
				g.writeEndArray();
				
				g.writeEndObject();
			}
		}
		g.writeEndArray();
	}
	
	private String getReportJSON(CorrelationReport report) throws IOException {
		StringWriter sw = new StringWriter();
		JsonFactory f = new JsonFactory();
		JsonGenerator g = f.createJsonGenerator(sw);

		g.writeStartObject();
		g.writeStringField("product", report.getProduct());
		g.writeStringField("version", report.getProductVersion());
		g.writeStringField("os", report.getOs().getName());
		OperatingSystem os = report.getOs();
		
		for (Map.Entry<String, Signature> entry : os.getSignatures().entrySet()) {
			Signature sig = entry.getValue();
			g.writeStringField("signature", sig.getName());
			g.writeStringField("crash-reason", sig.getReason());
			
			g.writeArrayFieldStart("core-counts");
			for (Map.Entry<String, Integer> sigCoreEntry : sig.getSortedCoreCounts()) {
				
				float sigRatio = sig.getCount() > 0 ? (float)sigCoreEntry.getValue() / (float)sig.getCount() : 0.0f;
				int osCount = os.getCoreCounts().get(sigCoreEntry.getKey());
				float osRatio = os.getCount() > 0 ? (float)osCount / (float)os.getCount() : 0.0f;
				
				g.writeStartObject();
				g.writeStringField("arch", sigCoreEntry.getKey());
				g.writeNumberField("sc", sigCoreEntry.getValue());
				g.writeNumberField("tsc", sig.getCount());
				g.writeNumberField("sp", (int)(sigRatio * 100.0f));
				g.writeNumberField("oc", osCount);
				g.writeNumberField("toc", os.getCount());
				g.writeNumberField("op", (int)(osRatio * 100.0f));
				g.writeEndObject();
			}
			g.writeEndArray();
			
			generateJSONArray(g, "interesting-modules", "module", os, sig, false, true);
			generateJSONArray(g, "interesting-addons", "addon", os, sig, true, true);

		}

		g.writeEndObject();
		g.close();
		
		return sw.toString();
	}
	
	@GET
	@Path("report/{date}/{product}/{version}/{os}/{signature}")
	@Produces("application/json")
	public String getReport(@PathParam("date") String date, @PathParam("product") String product, @PathParam("version") String version, 
							@PathParam("os") String os, @PathParam("signature") String signature) {
		String json = "";
		try {
			CorrelationReport report = ccDao.getReport(date, product, version, os, signature);
			json = getReportJSON(report);
		} catch (IOException e) {
			LOG.error("Problem getting or serializing report", e);
			throw new WebApplicationException(e, Response.Status.INTERNAL_SERVER_ERROR);
		}
		
		return json;
	}
	
	@GET
	@Path("top-crashers/{date}/{product}/{version}/{os}")
	@Produces("text/html")
	public String getTopCrashers(@PathParam("date") String date, @PathParam("product") String product, @PathParam("version") String version, 
								 @PathParam("os") String os) {
		StringBuilder sb = new StringBuilder();
		try {
			List<Signature> signatures = ccDao.getTopCrashers(date, product, version, os);
			sb.append("<html><body>");
			for (Signature sig : signatures) {
				if (sig.getCount() > MIN_SIG_COUNT) {
					// TODO: Producing HTML for now but probably will do JSON in the future
					String linkUrl = "/correlation-report/report/" + date + "/" + product + "/" + version + "/" + os + "/" + java.net.URLEncoder.encode(sig.getName(), "UTF-8");
					sb.append("<span><a href=\"").append(linkUrl).append("\">");
					sb.append(sig.getName()).append("</a> (").append(sig.getCount()).append(") ").append("</span><br/>\n");
				}
			}
			sb.append("</body></html>");
		} catch (IOException e) {
			LOG.error("Problem getting or serializing report", e);
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

			ccDao.incrementCounts(date, product, version, os, signature, arch, moduleVersions, addonVersions);
		} catch (IOException e) {
			LOG.error("Problem getting or serializing report", e);
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
