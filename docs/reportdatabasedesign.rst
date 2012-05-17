.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: reportdatabasedesign

.. _reportdatabasedesign-chapter:


Report Database Design
======================

Introduction
------------

With the launch of [[MeanTimeBeforeFailure]] and :ref:`topcrashersbyurl-chapter`
reports, we have added 8 new database tables. The call into the
following categories:

* configuration
   * mtbfconfig
   * tcbyurlconfig
* facts
   * mtbffacts
   * topcrashurlfacts
* dimensions
   * productdims
   * urldims
   * signaturedims
* relational
   * topcrashurlfactsreports

What relational? Aren't they all?

Star Schema
-----------

Taking inspiration from data warehousing, we implement the datastore
with dimensional modeling instead of relational modeling. The pattern
used star schemas. Our implementation is a very lightweight approach
as we don't automatically generate facts for every combination of
dimensions. This is not a Pentaho competitor :)

Star schemas are optimized for:

* read only systems
* large amounts of data
* viewed from different levels of granularity


Pattern
-------

The dimensions and facts are the heart of the pattern.

**dimensions**

Each dimension is property with various attributes and values at
different levels of granularity. Example::

  urldims - table would have columns:
  id
  domain
  url

Sample values

1. en-us.www.mozilla.com, ALL
2. http://en-us.www.mozilla.com/en-US/firefox/3.0.5/whatsnew/
3. en-us.www.mozilla.com, http://en-us.www.mozilla.com/en-US/firefox/features/

We see a dimension that describes the property "url". This is useful
for talking about crashes that happen on a specific url. We also see
two levels of granularity, a specific URL as well as all urls under a
domain.

Dimensions give us ways to slice and dice aggregate crash data, then
drill down or rollup this information.

Note: time could be a dimension ( and usually is in data warehouses ).
For MTBF and Top Crash By URl we don't treat it as a 1st class
dimension as their are no requirements to roll it up ( say to Q1
crashes, etc) and having it be a column in the facts table provides
better performance.


**facts**

For a given report it will be powered by a main facts table.

Example::

  topcrashurlfacts - table would have the columns:
  id
  count
  rank
  day
  productdims_id
  urldims_id
  signaturedims_id

A top crashers by url fact has two key elements, an aggregate crash
count and the rank respective to others facts. So if we have static
values for all dimensions and day, then we can see who has the most
crashes.

**Reporting**

The general pattern of creating a report is for a series of static and
1 or two variable dimensions, display the facts that meet this
criteria.
