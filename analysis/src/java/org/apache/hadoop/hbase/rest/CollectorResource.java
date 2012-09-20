/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package org.apache.hadoop.hbase.rest;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.text.ParseException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.BlockingQueue;

import javax.ws.rs.Consumes;
import javax.ws.rs.POST;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.WebApplicationException;
import javax.ws.rs.core.CacheControl;
import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.MultivaluedMap;
import javax.ws.rs.core.Response;
import javax.ws.rs.core.Response.ResponseBuilder;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import com.hazelcast.core.Hazelcast;
import com.mozilla.socorro.dao.hbase.HbaseCrashReportDao;
import com.sun.jersey.core.header.ParameterizedHeader;
import com.sun.jersey.multipart.BodyPart;
import com.sun.jersey.multipart.BodyPartEntity;
import com.sun.jersey.multipart.MultiPart;

@Path("/collector")
public class CollectorResource extends ResourceBase {

	private static final Log LOG = LogFactory.getLog(CollectorResource.class);

	private static CacheControl cacheControl;
	static {
		cacheControl = new CacheControl();
		cacheControl.setNoCache(true);
		cacheControl.setNoTransform(false);
	}

	private HbaseCrashReportDao crDao;
	private final BlockingQueue<String> unprocessedQueue;

	public CollectorResource() throws IOException {
		super();
		crDao = new HbaseCrashReportDao(servlet.getTablePool());
		unprocessedQueue = Hazelcast.getQueue("crash_reports_unprocessed_queue");
	}

	@POST
	@Consumes(MediaType.MULTIPART_FORM_DATA)
	@Produces(MediaType.TEXT_PLAIN)
	public Response collector(MultiPart multipart) {
		Map<String,String> fields = new HashMap<String,String>();
		byte[] dump = null;
		List<BodyPart> bodyParts = multipart.getBodyParts();
		for (BodyPart bp : bodyParts) {
			String fieldName = null;
			MultivaluedMap<String, ParameterizedHeader> paramHeaders;
			try {
				paramHeaders = bp.getParameterizedHeaders();
				for (Map.Entry<String, List<ParameterizedHeader>> entry : paramHeaders.entrySet()) {
					for (ParameterizedHeader pheader : entry.getValue()) {
						Map<String, String> parameters = pheader.getParameters();
						if (parameters.containsKey("name")) {
							fieldName = parameters.get("name");
						}
					}
				}
			} catch (ParseException e) {
				LOG.error("Error parsing headers", e);
				throw new WebApplicationException(e, Response.Status.INTERNAL_SERVER_ERROR);
			}

			if (bp.getMediaType().isCompatible(MediaType.TEXT_PLAIN_TYPE)) {
				String fieldValue = bp.getEntityAs(String.class);
				if (fieldName != null) {
					fields.put(fieldName, fieldValue);
				}
			} else if (MediaType.APPLICATION_OCTET_STREAM.equals(bp.getMediaType().toString())) {
				BodyPartEntity bpe = (BodyPartEntity)bp.getEntity();
				InputStream is = null;
				try {
					ByteArrayOutputStream baos = new ByteArrayOutputStream();
					byte[] buffer = new byte[32768];
					is = bpe.getInputStream();
					int read = 0;
					while ((read = is.read(buffer)) != -1) {
						baos.write(buffer, 0, read);
					}

					dump = baos.toByteArray();
				} catch (IOException e) {
					LOG.error("Error while reading binary dump", e);
					throw new WebApplicationException(e, Response.Status.INTERNAL_SERVER_ERROR);
				} finally {
					try {
						is.close();
					} catch (IOException e) {
						LOG.error("Error while closing binary dump input stream", e);
						throw new WebApplicationException(e, Response.Status.INTERNAL_SERVER_ERROR);
					}
				}
			}
		}

		String ooid = null;
		if (fields.size() > 0 && dump != null) {
			try {
				ooid = crDao.insert(fields, dump);
				unprocessedQueue.put(ooid);
			} catch (IOException e) {
				LOG.error("Error while insert/updating crash reports table", e);
				throw new WebApplicationException(e, Response.Status.INTERNAL_SERVER_ERROR);
			} catch (InterruptedException e) {
				LOG.error("Interrupted while putting ooid in unprocessed queue: " + ooid, e);
				throw new WebApplicationException(e, Response.Status.INTERNAL_SERVER_ERROR);
			}
		}

		ResponseBuilder response = null;
		if (ooid != null) {
			response = Response.ok(ooid);
		} else {
			response = Response.status(Response.Status.NOT_MODIFIED);
		}
		response.cacheControl(cacheControl);
		return response.build();
	}

}
