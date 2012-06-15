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
