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

import java.io.IOException;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.servlet.*;
import org.eclipse.jetty.servlet.ServletContextHandler; 

import com.google.inject.servlet.GuiceFilter;

public class CorrelationReportServer {

	public static void main(String[] args) throws Exception {
		int port = Integer.parseInt(System.getProperty("server.port", "8080"));
		Server server = new Server(port);
		ServletContextHandler root = new ServletContextHandler(server, "/", ServletContextHandler.SESSIONS);
		
		root.addFilter(GuiceFilter.class, "/*", 0);
		root.addEventListener(new GuiceConfig());
		
		// This is really dumb but you have to have a servlet in order for the filter to kick in
		root.addServlet(new ServletHolder(new HttpServlet() {
			private static final long serialVersionUID = 1L;

			protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
				throw new IllegalStateException("unable to service request");
			}
			
		}), "/*");
		
		server.start();
		server.join();
	}
	
}
