package com.mozilla.socorro.web;

import javax.ws.rs.*;

@Path("/correlation-report")
public class CorrelationReportService {

	@GET
	@Path("core-count")
	public String getCoreCount(@PathParam("product") String product, @PathParam("version") String version, @PathParam("os") String os, @PathParam("signature") String signature) {
		StringBuilder sb = new StringBuilder();
		sb.append("product=").append(product).append("\n");
		sb.append("version=").append(version).append("\n");
		sb.append("os=").append(os).append("\n");
		sb.append("signature=").append(signature).append("\n");
		
		return sb.toString();
	}
	
	@GET
	@Path("interesting-modules")
	public String getInterestingModules(@PathParam("product") String product, @PathParam("version") String version, @PathParam("os") String os, @PathParam("signature") String signature) {
		StringBuilder sb = new StringBuilder();
		sb.append("product=").append(product).append("\n");
		sb.append("version=").append(version).append("\n");
		sb.append("os=").append(os).append("\n");
		sb.append("signature=").append(signature).append("\n");
		
		return sb.toString();
	}
}
