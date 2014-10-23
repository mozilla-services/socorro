.. index:: topcrashersbyurl

.. _topcrashersbyurl-chapter:


Top Crashers By URL
===================

Introduction
------------

The Top Crashers By Url report displays aggregate crash counts by
unique urls or by unique domains. From here one can drill down to
crash signatures. For crashes with comments, we display the comment in
a link to the individual crash. In the future, signatures will be
linked to search results, once we support url/domain as a search
parameter.       

Details
-------

**Data Definitions**

Urls - This is everything before the query string. Domains - This is
the entire hostname.   


**Examples**::

    http://www.example.com/page.html?foo=bar 

* url - http://www.example.com/page.html
* domain - www.example.com

    chrome://example/content/extension.xul 

* url - chrome://example/content/extension.xul
* domain - example 

    about:config 

invalid, no protocol

Filtering
---------

For a crash report to be counted it much have the following:

* A url which is not null or empty and which has a protocol
* Aggregates are calculated 1 day at a time for the previous day
* At the level of aggregation, it must have more than 1 record 

Crash data viewed from the url perspective is a very long tail of
crashes for a single unique url. We cut off this tail which reduces
data storage and processing time by an order of magnitude.    

A consequence of this filtering (only good urls + multiple crashes)
makes the total crash aggregates much lower than top crashers or raw
queries. Keep this in mind when using aggregates: Top crashers (by os)
is a much better gauge.      


Administration
--------------

**Configuring new products**

The Top Crashers By URl report is powered by the tcbyurlconfig and
productdims tables. 

1. Make sure your product is in the productdims table
    1. If not, insert it. The following sets up a specific version of
       a specific product for all, win, and mac platforms.::   

          INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.4', 'ALL','major');
          INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.4', 'Win','major');
          INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.4', 'Mac','major');

2. Insert a config entry for the exact product you want to report on.
   usually this is os_name = ALL.::  

      INSERT INTO tcbyurlconfig (productdims_id, enabled) 
      SELECT id, 'Y' FROM productdims WHERE product = 'Firefox' AND version = '3.0.4' AND os_name = 'ALL';

3. wait for results
4. reap the profit. 

**Suspending Reports**

Table tcbyurlconfig has an 'enabled' column. Set it false to stop the
cron from updating the reports for a particular product.    

**Mozilla Specific**

Make sure to match up the release type. versions with pre are
milestone. Versions with a or b in them are development.   

Operations
----------

This report is populated by a cron python script which runs at 10:00
PM PST. The run is controlled by configuration data from a table in
the database. All products which are enabled in this config table will
have their daily report generated.      

In future this will be managed via an admin page, but currently it is
managed via SQL.   


Development
-----------

Details about the database design are in :ref:`reportdatabasedesign-chapter`
