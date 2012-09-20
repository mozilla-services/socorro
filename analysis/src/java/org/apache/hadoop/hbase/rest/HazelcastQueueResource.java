/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package org.apache.hadoop.hbase.rest;

import java.io.IOException;
import java.util.concurrent.BlockingQueue;

import javax.ws.rs.Consumes;
import javax.ws.rs.GET;
import javax.ws.rs.POST;
import javax.ws.rs.PUT;
import javax.ws.rs.*;
import javax.ws.rs.Produces;
import javax.ws.rs.WebApplicationException;
import javax.ws.rs.core.CacheControl;
import javax.ws.rs.core.Context;
import javax.ws.rs.core.Response;
import javax.ws.rs.core.UriInfo;
import javax.ws.rs.core.Response.ResponseBuilder;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.hbase.rest.model.QueueStringModel;

import com.hazelcast.core.Hazelcast;

@Path("/hazelcast/{queueName}")
public class HazelcastQueueResource extends ResourceBase {

	private static final Log LOG = LogFactory.getLog(HazelcastQueueResource.class);

	private static CacheControl cacheControl;
	static {
		cacheControl = new CacheControl();
		cacheControl.setNoCache(true);
		cacheControl.setNoTransform(false);
	}

	private final String queueName;
	private final BlockingQueue<String> q;

	public HazelcastQueueResource(@PathParam("queueName") String queueName) throws IOException {
		super();
		this.queueName = queueName;
		q = Hazelcast.getQueue(this.queueName);
	}

	private Response addToQueue(QueueStringModel model) {
		try {
			q.put(model.getValue());
		} catch (InterruptedException e) {
			throw new WebApplicationException(e, Response.Status.INTERNAL_SERVER_ERROR);
		}
		return Response.ok().build();
	}

	@GET
	@Produces( { MIMETYPE_TEXT, MIMETYPE_JSON, MIMETYPE_XML })
	public Response get(final @Context UriInfo uriInfo) {
		if (LOG.isDebugEnabled()) {
			LOG.debug("GET " + uriInfo.getAbsolutePath());
		}
		servlet.getMetrics().incrementRequests(1);
		String ooid = q.poll();
		if (ooid == null) {
			throw new WebApplicationException(Response.Status.NO_CONTENT);
		}

		QueueStringModel model = new QueueStringModel(ooid);
		ResponseBuilder response = Response.ok(model);
		response.cacheControl(cacheControl);
		return response.build();
	}

	@PUT
	@Consumes( { MIMETYPE_TEXT, MIMETYPE_JSON, MIMETYPE_XML })
	public Response put(final QueueStringModel model, final @Context UriInfo uriInfo) {
		if (LOG.isDebugEnabled()) {
			LOG.debug("PUT " + uriInfo.getAbsolutePath());
		}
		servlet.getMetrics().incrementRequests(1);

		return addToQueue(model);
	}

	@POST
	@Consumes( { MIMETYPE_TEXT, MIMETYPE_JSON, MIMETYPE_XML })
	public Response post(final QueueStringModel model, final @Context UriInfo uriInfo) {
		if (LOG.isDebugEnabled()) {
			LOG.debug("PUT " + uriInfo.getAbsolutePath());
		}
		servlet.getMetrics().incrementRequests(1);

		return addToQueue(model);
	}
}
