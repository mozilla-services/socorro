2.3.5 Upgrade
=============

This upgrade focuses entirely on creating the FennecAndroid "product" 
and related required database changes.  None of the below require 
backfilling, and as such should run quite quickly, with one noted 
exception.

706807
	Add productID column to reports.
	
	WARNING: this requires obtaining a lock on the reports table. 
	As such, it may take up to several minutes to get that lock or
	even abort.  If it aborts, re-run the upgrade after waiting a
	few minutes.
	
706893
	Add FennecAndroid to products list.
	
706900
	Add Product-AppID mapping table for use of processors.
	
706899
	Modify update_product_versions to pull FennecAndroid builds
	from releases_raw.
	
