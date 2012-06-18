#.# Database Updates
====================

This batch makes the following database changes:

bug #759724
	Add new product "WebRuntime" to all product-related tables.
	Modify update_products to create products and builds for WebRuntime
	as a duplicate of Firefox releases starting with version
	15.0.

...

The above changes should take only a few minutes to deploy.
This upgrade does not require a downtime.