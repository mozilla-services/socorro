# Run stackwalk as subprocess

- Status: accepted
- Deciders: Will Kahn-Greene, and Socorro team circa 2008
- Date: 2021-08-19
- Tags: processor, stackwalk

NOTE(willkg): This was decided years ago. First commit for running stackwalk as
a subprocess [is 2008](https://github.com/mozilla-services/socorro/commit/b6a49302918440e896135a2b6b0b82e25f7aa793).
Discussion of options and what was chosen isn't available. Further, the world has
changed radically since then, so it's prudent to re-up this decision.

## Context and Problem Statement

The Socorro processor needs to extract information from the minidump, walk the
stack of the crashing process, and symbolicate the frames. The stackwalker is a
separate project that uses the Breakpad library and is written in C++.
How should the processor run stackwalk on minidumps?

## Decision Drivers

- processor is written in Python; stackwalk is written in C++
- stackwalk code has equivalent code in mozilla-central and the two are
  developed in tandem
- minidumps can be malformed; stackwalk can hang and crash

## Considered Options

- Option 1: wrap C++ code in a microservice with an API used by processor
- Option 2: wrap C++ code as a Python library
- Option 3: run C++ code as a subprocess

## Decision Outcome

Chose Option 3: run C++ code as a subprocess because it's the simplest
implementation that allows stackwalk to hang and crash without crashing the
processor.

### Positive Consequences

- running stackwalk as a subprocess makes it easy to swap out for another
  executable which makes the Rust rewrite a lot easier to do

## Pros and Cons of the Options

### Option 1: wrap C++ code in a microservice with an API used by processor

Wrap the stackwalk code in a microservice that exposes a public API for
extracting information from minidumps.

Goods:

- allows independent stackwalk development making it easier to keep
  mozilla-central and stackwalk code in sync
- stackwalk crashing doesn't crash the processor
- exposing as an API might enable engineering to do other things; Sentry's
  Symbolicator service exposes minidump stackwalking as an API

Bads:

- microservices require infrastructure, deploy pipelines, monitoring, and SRE
  resources to run
- creating a microservice adds to our day-to-day maintenance for the system

### Option 2: wrap C++ code as Python library

We can use something like Cython to wrap the C++ code such that it can be
imported and used in Python code.

Goods:

- we can make a Pythonic API for using the stackwalk code
- runs in-process with processor so we don't incur the performance costs of
  running subprocesses

Bads:

- we'd have to write and maintain the wrapper; Python does a good job making
  this sort of thing straight-forward, but this is the only thing we'd be
  wrapping and it's a set of technologies that require a level of expertise to
  maintain
- wrapping C++ in Python doesn't help with hangs and crashes--it'll take out
  the entire processor process in a way we can't easily tell which minidumps
  are problematic

### Option 3: run C++ code as a subprocess

We can compile stackwalk as a command line executable and run it as a
subprocess.

Goods:

- malformed minidumps and bugs in the stackwalker that cause hangs and segfaults don't take out the processor
- it's easy to know which minidumps are problematic

Bads:

- there's a performance penalty for running subprocesses; this does add up, but
  it's a fraction of the time it takes to extract information from the
  minidump, download and parse SYM files, and symbolicate stacks
- we have to pass inputs to and outputs from stackwalk through command line
  execution
- we have to use temp files
- we have to differentiate between program output and program diagnostic
  output; we can use stderr stdout, but sometimes this is problematic
