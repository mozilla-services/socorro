2.4.3 Database Updates
======================

This batch makes the following database changes:

bug 721456
	Fix version sort to handle 3-digit betas and final betas properly.
	
no bug
	Fix issue with rerunnability of the socorro version update function.
	
bug 687906 
	Add new user "analyst" with read-only permissions to many tables
	NOTE: for this to be useful, the analyst user needs to be added
		to pgbouncer, and a password needs to be set for the user
		These need to be done in manual post-upgrade steps.
		
bug 681476
	Remove Frames table.
	
bug 725732
	Exclude ESR releases from product_versions (for the time being).

The above changes should take only a few minutes to deploy.
This upgrade does not require a downtime.