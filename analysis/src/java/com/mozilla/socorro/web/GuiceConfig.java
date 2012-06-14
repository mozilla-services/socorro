/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package com.mozilla.socorro.web;

import org.guiceyfruit.jsr250.Jsr250Module;

import com.google.inject.Guice;
import com.google.inject.Injector;
import com.google.inject.servlet.GuiceServletContextListener;
import com.google.inject.servlet.ServletModule;
import com.mozilla.socorro.dao.CrashCountDao;
import com.mozilla.socorro.dao.hbase.HbaseCrashCountDao;
import com.sun.jersey.guice.spi.container.servlet.GuiceContainer;

public class GuiceConfig extends GuiceServletContextListener {

	@Override
	protected Injector getInjector() {

		return Guice.createInjector(new Jsr250Module(), new ServletModule() {
			@Override
			protected void configureServlets() {
				bind(CrashCountDao.class).to(HbaseCrashCountDao.class);
				bind(CorrelationReportService.class);

				serve("*").with(GuiceContainer.class);
			}
		});
	}

}
