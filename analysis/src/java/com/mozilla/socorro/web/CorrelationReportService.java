package com.mozilla.socorro.web;

import gnu.trove.TObjectIntIterator;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.StringWriter;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Map;

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
	
	private final CrashCountDao ccDao;
	private static final SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMdd");
	private static final ObjectMapper jsonMapper = new ObjectMapper();
	
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
		
		g.writeObjectFieldStart("core-counts");
		TObjectIntIterator<String> iter = report.getCoreCountsIterator();
		while (iter.hasNext()) {
			iter.advance();
			g.writeObjectFieldStart("core-count");
			g.writeStringField("cores", iter.key());
			g.writeNumberField("count", iter.value());
			g.writeEndObject();
		}
		g.writeEndObject();
		
		g.writeObjectFieldStart("interesting-modules");
		iter = report.getModuleVersionCountsIterator();
		while (iter.hasNext()) {
			iter.advance();
			g.writeObjectFieldStart("module");
			g.writeStringField("name", iter.key());
			g.writeNumberField("count", iter.value());
			g.writeEndObject();
		}
		g.writeEndObject();
		
		g.writeObjectFieldStart("interesting-addons");
		iter = report.getModuleVersionCountsIterator();
		while (iter.hasNext()) {
			iter.advance();
			g.writeObjectFieldStart("addon");
			g.writeStringField("name", iter.key());
			g.writeNumberField("count", iter.value());
			g.writeEndObject();
		}
		g.writeEndObject();

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
			CorrelationReport report = ccDao.getReport(sdf.parse(date), product, version, os, signature);
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
			Map<String,Object> archModuleMap = jsonMapper.readValue(request.getInputStream(), new TypeReference<Map<String,Object>>() { });
			String arch = (String)archModuleMap.get("arch");
			Map<String,String> moduleVersions = (Map<String,String>)archModuleMap.get("module-version");
			Map<String,String> addonVersions = (Map<String,String>)archModuleMap.get("addon-version");

			ccDao.incrementCounts(sdf.parse(date), product, version, os, signature, arch, moduleVersions, addonVersions);
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
