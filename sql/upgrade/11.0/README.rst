11.0 Database Updates
=====================

This batch makes the following database changes:
	
bug #752074
	Add new functions for adding a manual release to releases_raw,
	and changing the featured versions.
	Some changes based on the middlewaer implementation.
	
bug #748425
	Enable choosing a default product via the default_versions view,
	as well as product and channel sort columns
	
No bug
	Add crontabber state backup table
	Per discussion socorro staff meeting 5/23
	
bug 629062
	Grant "analyst" permissions on explosiveness
	
...

The above changes should take only a few minutes to deploy.
This upgrade does not require a downtime.