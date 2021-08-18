# Separate collector into new repo

- Status: accepted
- Deciders: Rob Helmer, Lonnen, Will Kahn-Greene
- Date: 2015-03-20
- Tags: collector

Technical Story: https://bugzilla.mozilla.org/show_bug.cgi?id=1145703

Aftermath blog post: https://bluesock.org/~willkg/blog/mozilla/antenna_project_wrapup.html

## Context and Problem Statement

The Socorro collector has a different set of uptime requirements, risk profile,
and maintenance needs. How can we account for that in the Socorro crash
ingestion pipeline architecture?

## Decision Drivers

- support different risk profiles for the collector and the rest of Socorro in
  regards to code changes and deployments
- support independent development of the collector and the rest of Socorro

## Considered Options

- Option 1: separate collector into new project
- Option 2: continue collector development in Socorro repo, but support
  multiple deploy pipelines
- Option 3: do nothing

## Decision Outcome

Chosen option 1 "separate collector into new project" because it attains our
goals in a way that minimizes new complexity to our deploy infrastructure and
also gives us the flexibility to rewrite components individually improving our
technical debt situation.

### Positive consequence

- in breaking out the collector as a separate project, we ended up rewriting it
  shedding a lot of technical debt
- in rewriting the collector, we ended up with a specification for the payload
  format which enabled work on crash reporter clients

## Pros and Cons of the Options

### Option 1: separate collector into separate project

This option covers separating the collector into a new project with its own
GitHub repository and deploy pipeline.

Goods:

- we can deploy the collector independently from the rest of Socorro and
  vice versa
- we can reduce risk of losing crash reports without affecting development of
  the rest of Socorro
- we can rewrite the collector without having to rewrite all of Socorro at the
  same time--this lets us address several long-standing technical debt issues

Bads:

- adds to overall maintenance burden of the project (additional project
  scaffolding, duplicate code, standards, etc)
- migration projects that involve the boundary between the collector and
  processor will need to be done in coordinated steps which makes them more
  complex and risky

### Option 2: stay in same repo, but add additional deploy pipeline

This option covers keeping the code in the same repo (monorepo style) but
changing the deploy infrastructure and triggers so that we can deploy the
collector independently of the rest of Socorro.

Goods:

- we can deploy the collector independently from the rest of Socorro and
  vice versa
- we can reduce risk of losing crash reports without affecting development of
  the rest of Socorro

Bads:

- shared code between the collector and the rest of Socorro continues to change
  even if we're not doing deploys which makes deploys more risky
- deploy infrastructure is more complicated because it needs two different
  triggers that drive two different pipelines

### Option 3: do nothing

While this problem is annoying, we can live with it.

Goods:

- no additional work done on this project

Bads:

- slower overall development of Socorro for the foreseeable future
