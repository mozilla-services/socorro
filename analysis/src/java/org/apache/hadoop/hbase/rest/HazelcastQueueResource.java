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
