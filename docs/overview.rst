========
Overview
========

What is Socorro?
================

Socorro is software that implements a crash ingestion pipeline.

The Socorro code is hosted in a GitHub repository at
`<https://github.com/mozilla-services/socorro>`_ and released and distributed
under the Mozilla Public License v2.

The crash ingestion pipeline that we have at Mozilla looks like this:

.. graphviz::

   digraph G {
      rankdir=LR;
      splines=lines;

      subgraph coll {
         rank=same;

         client [shape=box3d, label="firefox"];
         collector [shape=rect, label="collector"];
      }

      subgraph stores {
         rank=same;

         aws [shape=tab, label="S3", style=filled, fillcolor=gray];
      }

      subgraph proc {
         rank=same;

         pigeon [shape=cds, label="pigeon"];
         processor [shape=rect, label="processor"];
         rabbitmq [shape=tab, label="RMQ", style=filled, fillcolor=gray];
      }

      subgraph stores2 {
         rank=same;

         postgres [shape=tab, label="Postgres", style=filled, fillcolor=gray];
         elasticsearch [shape=tab, label="Elasticsearch", style=filled, fillcolor=gray];
         telemetry [shape=tab, label="Telemetry (S3)", style=filled, fillcolor=gray];
      }

      subgraph processing {
         rank=same;

         crontabber [shape=rect, label="crontabber"];
         webapp [shape=rect, label="webapp"];
      }


      pigeon -> rabbitmq [label="crash id"];
      aws -> pigeon [label="S3:PutObject"];

      client -> collector [label="HTTP"];
      collector -> aws [label="save raw"];

      rabbitmq -> processor [label="crash id"];
      aws -> processor [label="load raw"];
      processor -> { aws, postgres, elasticsearch, telemetry } [label="save processed"];

      postgres -> webapp;
      aws -> webapp [label="load raw,processed"];
      elasticsearch -> webapp;

      postgres -> crontabber;
      elasticsearch -> crontabber;

      { rank=min; client; }
   }


Arrows direction represents the flow of interesting information like saving
crash information, loading crash information, pulling crash ids from queues, and
so on.

Important services in the diagram:

* **Collector:** Collects incoming crash reports via HTTP POST. The collector
  we use is called `Antenna <https://antenna.readthedocs.io/>`_. It saves
  crash data to AWS S3.
* **Processor:** Extracts data from minidumps, generates crash signatures,
  performs other analysis, and saves everything as a processed crash.
* **Webapp (aka Crash Stats):** Web user interface for analyzing crash data.
* **Crontabber:** Runs hourly/daily/weekly tasks for analyzing and processing
  data.

The processor stores crash data in several crash storage destinations:

* S3
* Postgres
* Elasticsearch
* Telemetry (S3)


Repository structure
====================

Top-level folders
-----------------

If you clone our `git repository
<https://github.com/mozilla-services/socorro>`_, you will find the following
folders.

Here is what each of them contains:

**alembic/**
    Alembic-managed database migrations.

**bin/**
    Some scripts that should get moved to a more sensible place but haven't,
    yet.

**config/**
    Configuration for an old way of running Socorro that you can completely
    ignore.

**docker/**
    Docker environment related scripts, configuration, and other bits.

**docs/**
    Documentation of the Socorro project (you're reading it right now).

**e2e-tests/**
    The Selenium tests for the webapp.

**minidump-stackwalk/**
    The minidump stackwalker program that the processor runs for pulling
    out information from crash report dumps.

**requirements/**
    Files that hold Python library requirements information.

**scripts/**
    Arbitrary scripts.

**socorro/**
    The bulk of the Socorro source code.

**tools/**
    Some files that should get moved, but haven't, yet.

**webapp-django/**
    The webapp source code.

**wsgi/**
    Another part of the webapp.
