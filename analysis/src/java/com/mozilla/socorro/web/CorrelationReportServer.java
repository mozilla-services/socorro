/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
