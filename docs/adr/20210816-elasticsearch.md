# Use Elasticsearch for search

- Status: accepted
- Deciders: Socorro team circa 2011
- Date: 2011-04-19
- Tags: search

Technical Story: https://bugzilla.mozilla.org/show_bug.cgi?id=651279

## Context and Problem Statement

Crash investigation requires ad-hoc querying of our existing crash data. Over even a limited set of fields, Postgres search was taking 30 - 300 seconds (https://bugzilla.mozilla.org/show_bug.cgi?id=652880, https://bugzilla.mozilla.org/show_bug.cgi?id=710091) or longer to return results. We also wanted full-text search over the frame data, or at least signatures (https://bugzilla.mozilla.org/show_bug.cgi?id=465360). We were running our own hardware in our own data center, so scaling up existing hardware was non-trivial. What technologies could enable fast, freeform querying over a recent set of all crash reports?

## Considered Options

- Option 1: PostgreSQL Full-Text Search
- Option 2: Hadoop / Map-Reduce
- Option 3: Elasticsearch

## Decision Outcome

Chose Elasticsearch because

- We could not scale up to a larger single machine for postgresql
- HBase and Hadoop were unstable and only usable by developers, while most of our search users were non-developers triaging issues
- Elasticsearch cluster was recently adopted by for input.mozilla.org, and it had a clearer path to scalability

## Pros and Cons of the options

### Option 1: PostgreSQL

PostgresSQL (Postgres) is a free and open-source relational database management system with full text indexing and search over natural-language text fields, in addition to standard SQL. Database Driver written in C with a python wrapper.

Postgres 9.0 documentation:

https://www.postgresql.org/docs/9.0/index.html

Goods:

- already in production
- supports search over text fields
- efficient data storage with views and stored procedures

Bads:

- already pushing the boundaries (largest publicly-known database at the time)
- unable to expand to accomodate additional fields
- hourly and daily stored procedures were already taking longer than their interval to run

### Option 2: Hadoop / Map-Reduce

Hbase is an open-source, non-relational distributed database modeled after Google's Bigtable.

cannot find HBase 0.2 documentation now, or HBase 0.92, so here is the HBase 0.98 documentation: http://www.devdoc.net/bigdata/hbase-0.98.7-hadoop1/book/book.html

Goods:

- distributed across many machines and able to scale
- already in use as primary raw crash store of record
- map-reduce emerging as a best practice handling data too large for RDBMS

Bads:

- cluster was run on post-warranty seagate micro with failing hardware
- pre-1.0 with no operations support interally; metrics team administering the cluster
- thrift
- queries are small programs that have to be written by engineers; most crash investigators don't write software

### Option 3: Elasticsearch

Elasticsearch is a distributed, free and open search and analytics engine for
all types of data, including textual, numerical, geospatial, structured, and
unstructured. Based on Lucene. REST APIs. Python client.

Elasticsearch 1.4 documentation:

https://www.elastic.co/guide/en/elasticsearch/reference/1.4/index.html

Goods:

- supports searching using filters
- supports faceting/aggregations
- supports partitioning indexes by time and searching/faceting across
  indexes; this allows us to easily expire old data from storage
- supports flexible indexing strategies allowing us to easily add new fields
- supports updating records when reprocessing
- has Python client library

Bads:

- Socorro uses Postgres and hbase; adding Elasticsearch to the mix is a lot to
  ask for people setting up Socorro
