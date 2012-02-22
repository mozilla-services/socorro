2.5.0 Database Updates
======================

This batch makes the following database changes:

bug #729195
	Modify Postgres database to correctly handle ESR releases.

The above changes should take around 1 hour to deploy.

This upgrade should involve a halt to processing while 2.5 changes are deployed in order to ensure correct crash format.