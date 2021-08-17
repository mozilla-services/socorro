# Use Elasticsearch for search

- Status: accepted
- Deciders: Socorro team circa 2011
- Date: 2011-04-19
- Tags: search

Technical Story: https://bugzilla.mozilla.org/show_bug.cgi?id=651279

## Context and Problem Statement

Postgres powers TopCrashers report and other reports. What should we switch to
to power those reports and also support search and faceting needs?

## Considered Options

- Option 1: Elasticsearch

Project was using Postgres, but it's unknown what other alternatives were
looked at.

## Decision Outcome

Chose Elasticsearch because it met the criteria we had at the time.

## Pros and Cons of the options

### Option 1: Elasticsearch

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
