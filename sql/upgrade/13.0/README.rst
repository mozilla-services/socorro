#.# Database Updates
====================

This batch makes the following database changes:

bug 764468
	replace existing processor ganglia views with a new
	view based on server_status
	
bug 763552
	make add_new_releases() better for ftpscraper
	
...

The above changes should take only a few minutes to deploy.
This upgrade does not require a downtime.  This upgrade will 
break ganglia monitoring which is already displaying incorrect
results.