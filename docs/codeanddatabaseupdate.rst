.. index:: codeanddatabaseupdate

.. _codeanddatabaseupdate-chapter:


Code and Database Update
========================

Socorro Wish List
-----------------

One of my (griswolf) directives is approximately "make everything work
efficiently and the same." Toward this end, there are several tasks:

Probably most important, we have an inefficient database design, and
some inefficient code working with it.

Next, we have a collection of 'one-off' code (and database schemas)
that could be more easily maintained using a common infrastructure,
common coding conventions, common schema layout, common patterns.

Finally, we have enhancement requests that would become more feasible
after such changes: Such requests would be more easily handled in a
cleaner programming environment; and in a cleaner environment there
might be fewer significant bugs, leaving more time to work on
enhancements.

Current state: See [[SocorroDatabaseSchema]]


Another Way to do Materialized Views?
-------------------------------------

The current system is somewhere between ad hoc reporting and a star
architecture. The main part of this proposal focuses on converting
further toward a star architecture. However there may be another way:
MapReduce techniques, which could possibly be run external to Mozilla
(for instance: Amazon Web Services) could be used to mine dump files
and create statistical data stored in files or database. Lars
mentioned to me that we now have some statistics folk on board who are
interested in this.


Database Design
---------------
* There are some legacy tables (reports, topcrasher) that are not normalized. Other tables are partly normalized. Non-normal has consequences:
    * Data is duplicated, causing possible synchronization issues.
        * JOSH: duplicated data is normal for materialized views and is not a problem a priori.
    * Data is duplicated, increasing size.
        * JOSH: I don't believe that the matview tables are that large, although we will want to look at partitioning them in the future because they will continue to grow.
        * FRANK: Lars points out that size-limiting partitions which reference each other must all be partitioned on the same key. This makes partitions a little more interesting
    * SELECT statements on multiple varchar fields, even when indexed, are probably slower than SELECT statements on a single foreign key. (And even if not, maintaining larger index tables has a time and space cost)
* There are legacy tables that contain deprecated columns, a slight inefficiency.
* In some cases, separable details are conflated, making it difficult to access by a single area of concern. For instance, the table that describes our products has an os_name column, requiring us to pretend we deal with an os named 'ALL' in order to examine product data without regard to os.
* According to Postgresql consultants, some types are not as efficient as others. Example TEXT (which we use only a little) is slightly more time-efficient than VARCHAR(n) (which we mostly use)
    * JOSH: this is a minor issue, and should only be changed if we're modifying the fields/tables anyway.
    * FRANK: We have already run into a size limitation for signatures which are now VARCHAR(255). Experiment shows that conversion to TEXT is slow because of index rebuilding, but conversion to VARCHAR(BIGGER_NUMBER) can be done by manipulating typemod (the number of chars in VARCHAR) in the system tables. So change from VARCHAR to TEXT needs to be scheduled in advance, with an expected 'long' turn around.
* Current indexes were carefully audited during PGExperts week. Schema changes will require careful reevaluation

Commonality
-----------

* Some of the tables that provide statistics (Mean Time Before Failure, for example) use a variant of the "Star" data warehousing pattern, which is well known and understood. Some do not. After discussion we have reached agreement that all should be partly 'starred'
    * osdims and productdims are appropriate dimension tables for each view that cares about operating system or product
    * url and signature 'dimension' tables are used to filter materialized views:
        * the 'fact' tables for views will use ids from these filter/dimension tables
        * the filter/dimension tables will hold only data that has passed a particular frequency threshold, initial guess at threshold: 3 per week.
* Python code has been written by a variety of people with various skill levels, doing things in a variety of ways. Mostly, this is acceptable, but required changes give us an opportunity.
* We now specify Python version 2.4, which is adequate. Possible to upgrade to 2.5.x or 2.6.x with both ease and safety. This is an opportunity to do so. No code needs to change for this.
* New features (safely) available in Python 2.5:
    * unified try/except/finally: instead of a try/finally block holding a try/except block
    * there is a very nice with: syntax useful for block-scoped non GC'd resources such as open files (like try: with an automatic finally: at block end)
    * generators are significantly more powerful, which might have some uses in our code
    * and lots more that seems less obviously useful to Socorro
    * better exception hierarchy
* New features (safely) available in Python 2.6
    * json library ships with Python 2.6
    * multiprocessing library parallel to threading library ships with Python 2.6
    * Command line option '-3' flags things that will work differently or fail in Python 3 (looking ahead is good)
* We use nosetests which is not correctly and fully functional in a Python 2.4 environment.

Viewable Interface
------------------

* We have been gradually providing a more useful view of the crash data. Sometimes this is intrinsically hard, sometimes it is made more difficult by our schema.
* We have requests for:
    * Better linkage between crash reports and bugs
    * Ability to view by OS and OS version, by signature, by product, by product version (some of this will be easier with a new schema)
    * Ability to view historical data, current data, (sliding) windows of data and trends
* Some of the requests seem likely to be too time or space costly. In some cases these might be feasible with a more efficient system

Consequences of Possible Changes
--------------------------------

 * (Only) Add new tables (two kinds of changes)
    * "replace in place", for instance add table reports_normal while leaving table reports in place)
    * "brand new", for instance add new productdims and osdims tables to serve a new tobcrashbysignature table
    * Existing views are not impacted (for good or ill)
    * Duplication of data (some tables near normal form, some not, etc) becomes worse than it now is
    * No immediate need to migrate data: Options
        * Maybe provide two views: "Historic" and "Current"
        * Maybe write 'orrible look-both-ways code to access both tables from single view
        * Maybe migrate data
    * Code that looks at old schema is (mostly?) unchanged
    * Code that looks at new schema is opportunity for improved design, etc.
    * Can do one thing at a time, with multiple 'easy' rollouts (each one is still a rollout, though)
    * Long term goal: Stop using old tables and code
* (Only) Drop redundant or deprecated columns in existing tables:
    * Existing views are no less useful, Viewer and Controller code will need some maintenance
    * Data migration is 'simple'
        * beware that dropped columns may be part of a (foreign) key or index
    * Data migration is needed at rollout
    * Minimally useful
* Optimize database types, indexes, keys:
    * Existing views are not much impacted
        * May want to optimize queries in Viewer and Controller code
        * May need to guard for field size or type in Controller code
    * Details of changes are 'picky' and may need some hand holding by consultants, maybe testing.
* Normalize existing tables (while adding new tables as needed):
    * Much existing code needs re-write
        * With different Model comes a need for different Viewers and Controllers
        * Opportunity to clarify old code
        * Opportunity to optimize queries
    * Data migration is needed at rollout
    * Rollout is complex (but need only one for complete conversion)
    * JOSH: in general, Matview generation should be optimized to be insert-only. In some cases, this will involve having a "current week" partition which gets dropped and recreated until the current week is completed. Updates are generally at least 4x as expensive as inserts.

Rough plan as of 2009 June
--------------------------

* Soon: Materialized views will make use of dimensions and 'filtered dimensions' tables
* Later: Normalize the 'raw' data to make use of tables describing operating system and product details. Leave signatures and urls raw

Specific Database Changes
-------------------------

**Star Data Warhousing**

**Existing tables**

* --dimension: signaturedims: associate the base crash signature
  string with an id-- Use signature TEXT directly
* dimension: productdims: associate a product, version, release and os_name with an id
    * os_name is neither sufficient for os drill-down (which wants os_version) nor properly part of a product dimension
* dimension: urldims: associate (a large number of) domains and urls, each pair with an id
* config: mtbfconfig: specifies the date-interval during which a given product (productdims) is of interest for MTBF analysis
* config: tcbyurlconfig: specifies whether a particular product (productdims) is now of interest for Top Crash by URL analysis.
* fact: mtbffacts: collects daily summary of average time before failure for each product
* --report: topcrashurlfactsreports: associates a crash uuid and a
  comment with a row of topcrashurlfacts ?Apparently never used?--

**Needed/Changed tables**

**Matview changes "Soon"**

* config (new): product_visibility: Specifies date interval during which a product (productdims id) is of interest for any view. ?Replaces mtbfconfig?
* dimension (new): osdims: associate an os name and os version with an id
* dimension (edit): productdims: remove the os_name column (replaced by another dimension osdims above)
* fact (replace): topcrashers: The table now in use to provide Top Crash by Signature view. Will be replaced by topcrashfacts
* fact (new): topcrashfacts: collect periodic count of crashes, average uptime before crash and rank of each signature by signature, os, product
    * replaces existing topcrashers table which is poorly organized for current needs
* config (new): tcbysignatureconfig: specify which products and operating systems are currently of interest for tcbysigfacts
* fact: (renamed, edit) top_crashes_by_url: collects daily summary of crashes by product, url (productdims, urldims)
* fact: (new): top_crashes_by_url_signature: associates a given row from top_crashes_by_url with one or more signatures

**Incoming (raw) changes "Later"**

* details (new): osdetails, parallel to osdims, but on the incoming side will be implemented later
* details (new): productdetails, parallel to productdims, but on the incoming side will be implemented later
* reports: Holds details of each analyzed crash report. It is not in normal form, which causes some ongoing difficulty
    * columns product, version, build should be replaced by productdetails foreign key later
    * column signature LARS: NULL is a legal value here. We'll have to make sure that we use left outer joins to retrieve the report records.
    * columns cpu_name, cpu_info are not currently in use in any other table, but could be a foreign key into cpudims
    * columns os_name, os_version should be replaced by osdims foreign key
    * columns email, user_id are deprecated and should be dropped

**Details**

**New or significantly changed tables**

New product_visibility table (soon, matview)::

 table product_visibility (
  id serial NOT NULL PRIMARY KEY,
  productdims_id integer not null,
  start_date timestamp, -- used by MTBF
  end_date timestamp,
  ignore boolean default False -- force aggregation off for this product id

New osdims table (soon, matview) NOTE: Data available only if
'recently frequent'::

 table osdims(
  id serial NOT NULL PRIMARY KEY,
  os_name TEXT NOT NULL,
  os_version TEXT);
  constraint osdims_key (os_name, os_version) unique (os_name, os_version);

Edited productdims table (soon, matview) NOTE: use case for adding
products is under discussion::

  CREATE TYPE release_enum AS ENUM ('major', 'milestone', 'development');
 table productdims (
  id serial NOT NULL PRIMARY KEY,
  product TEXT NOT NULL,
  version TEXT NOT NULL,
  release release_enum NOT NULL,
  constraint productdims_key (product, version) unique ( product, version )
  );

New product_details table (later, raw data) NOTE: All data will be
stored (raw data should not lose details)::

 table product_details (
  id serial NOT NULL PRIMARY KEY,
  product TEXT NOT NULL, -- /was/ character varying(30)
  version TEXT NOT NULL, -- /was/ character varying(16)
  release release_enum NOT NULL -- /was/ character varying(50) NOT NULL
  );

Edit mtbffacts to use edited productdims and new osdims (soon,
matview)::

 table mtbffacts (
  id serial NOT NULL PRIMARY KEY,
  avg_seconds integer NOT NULL,
  report_count integer NOT NULL,
  window_end timestamp, -- was DATE
  productdims_id integer,
  osdims_id integer
  constraint mtbffacts_key unique ( productdims_id, osdims_id, day );
  );

New top_crashes_by_signature table (soon, matview)::

 table top_crashes_by_signature (
  id serial NOT NULL PRIMARY KEY,
  count integer NOT NULL DEFAULT 0,
  average_uptime real DEFAULT 0.0,
  window_end timestamp without time zone,
  window_size interval,
  productdims_id integer NOT NULL,  -- foreign key. NOTE: Filtered by recent frequency
  osdims_id integer NOT NULL,       -- foreign key. NOTE: Filtered by recent frequency
  signature TEXT
  constraint top_crash_by_signature_key (window_end, signature, productdims_id, osdims_id) unique (window_end, signature, productdims_id, osdims_id)
  );
  -- some INDEXes are surely needed --

New/Renamed top_crashes_by_url table (soon, matview)::

 table top_crashes_by_url (
  id serial NOT NULL,
  count integer NOT NULL,
  window_end timestamp without time zone NOT NULL,
  window_size interval not null,
  productdims_id integer,
  osdims_id integer NOT NULL,
  urldims_id integer
  constraint top_crashes_by_url_key (uridims_id,osdims_id,productdims_id, window_end) unique (uridims_id,osdims_id,productdims_id, window_end)
  );

New top_crashes_by_url_signature (soon, matview)::

 table top_crash_by_url_signature (
  top_crashes_by_url_id integer, -- foreign key
  count integer NOT NULL,
  signature TEXT NOT NULL
  constraint top_crashes_by_url_signature_key (top_crashes_by_url_id,signature) unique (top_crashes_by_url_id,signature)
  );

New crash_reports table (later, raw view) Replaces reports table::

 table crash_reports (
  id serial NOT NULL PRIMARY KEY,
  uuid TEXT NOT NULL -- /was/ character varying(50)
  client_crash_date timestamp with time zone,
  install_age integer,
  last_crash integer,
  uptime integer,
  cpu_name TEXT, -- /was/ character varying(100),
  cpu_info TEXT, -- /was/ character varying(100),
  reason TEXT, -- /was/ character varying(255),
  address TEXT, -- /was/ character varying(20),
  build_date timestamp without time zone,
  started_datetime timestamp without time zone,
  completed_datetime timestamp without time zone,
  date_processed timestamp without time zone,
  success boolean,
  truncated boolean,
  processor_notes TEXT,
  user_comments TEXT, -- /was/ character varying(1024),
  app_notes TEXT, -- /was/ character varying(1024),
  distributor TEXT, -- /was/ character varying(20),
  distributor_version TEXT, -- /was/ character varying(20)
  signature TEXT,
  productdims_id INTEGER, -- /new/ foreign key NOTE Filtered by recent frequency
  osdims_id INTEGER, -- /new/ foreign key NOTE Filtered by recent frequency
  urldims_id INTEGER -- /new/ foreign key NOTE Filtered by recent frequency
  -- /remove - see productdims_id/ - product character varying(30),
  -- /remove - see productdims_id/ version character varying(16),
  -- /remove - redundant with build_date/ -- build character varying(30),
  -- /remove - see urldims_id/ url character varying(255),
  -- /remove - see osdims_id/ os_name character varying(100),
  -- /remove - see osdims_id/ os_version character varying(100),
  -- /remove - deprecated/ email character varying(100),
  -- /remove - deprecated/ user_id character varying(50),
  );
  -- This is a partitioned table: INDEXes are provided on date-based partitions

Tables with Minor Changes: varchar->text::

 table branches (
  product TEXT NOT NULL, -- /was/ character varying(30)
  version TEXT NOT NULL, -- /was/ character varying(16)
  branch TEXT NOT NULL, -- /was/ character varying(24)
  PRIMARY KEY (product, version)

 table extensions (
  report_id integer NOT NULL, -- foreign key
  date_processed timestamp without time zone,
  extension_key integer NOT NULL,
  extension_id TEXT NOT NULL, -- /was/ character varying(100)
  extension_version TEXT -- /was/ character varying(16)

 table frames (
  report_id integer NOT NULL,
  date_processed timestamp without time zone,
  frame_num INTEGER NOT NULL,
  signature TEXT -- /was/ varchar(255)
  );

 table priority_jobs
  uuid TEXT NOT NULL PRIMARY KEY -- /was/ varchar(255)

 table processors (
  id serial NOT NULL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE, -- /was/ varchar(255)
  startdatetime timestamp without time zone NOT NULL,
  lastseendatetime timestamp without time zone
  );

 table jobs (
  id serial NOT NULL PRIMARY KEY,
  pathname TEXT NOT NULL, -- /was/ character varying(1024)
  uuid TEXT NOT NULL UNIQUE, -- /was/ varchar(50)
  owner integer,
  priority integer DEFAULT 0,
  queueddatetime timestamp without time zone,
  starteddatetime timestamp without time zone,
  completeddatetime timestamp without time zone,
  success boolean,
  message TEXT,
  FOREIGN KEY (owner) REFERENCES processors (id)
  );

 table urldims (
  id serial NOT NULL PRIMARY KEY,
  domain TEXT NOT NULL, -- /was/ character varying(255)
  url TEXT NOT NULL -- /was/ character varying(255)
  key url    -- for drilling by url
  key domain -- for drilling by domain
  );

 table topcrashurlfactsreports (
  id serial NOT NULL PRIMARY KEY,
  uuid TEXT NOT NULL, -- /was/ character varying(50)
  comments TEXT, -- /was/ character varying(500)
  topcrashurlfacts_id integer
  );
