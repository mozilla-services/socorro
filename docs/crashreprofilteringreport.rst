.. index:: crashreprofilteringreport

.. _crashreprofilteringreport-chapter:


Crash Repro Filtering Report
============================

Introduction
------------

This page describes a report that assists in analyzing crash data for
a stack signature in order to try and reproduce a crash and develop a
reproducible test case.

Details
-------

for each release pull a data set of one weeks worth of data ranked by
signature like:

http://crash-stats.mozilla.com/query/query?do_query=1&product=Firefox&version=Firefox%3A3.0.10&date=&range_value=7&range_unit=days&query_search=signature&query_type=contains&query=

the provide a list like this with several fields of interest for
examing the data

Date Product Version Build OS CPU Reason Address Uptime Comments

but also need to add urls into the version of this report that is
behind auth. "reason" is not so helpful to me at this stage, but
others can weigh in on the idea of removing it.

maybe just make it include all these or allow users to pick the fields
it shows like bugzilla does?

Signature,Crash Address,UUIDProduct,Version,Build,OS,Time,Uptime,Last
Crash,URL,User Comments

anyway, get something close to what we have now in "Crash Reports in
PR_MD_SEND"

http://crash-stats.mozilla.com/report/list?product=Firefox&version=Firefox%3A3.0.10&query_search=signature&query_type=contains&query=&date=&range_value=7&range_unit=days&do_query=1&signature=_PR_MD_SEND

next allow the report user to apply filters to build more precise
queries from the set of reports.. filters might be from any of the
fields or it would really cool if we could also filter from other
items in the crash report like the full stack trace and/or module list::

        filter  uptime?  <  60 seconds
  and   filter  address? exactly_matches  0x187d000
  and   fliter  url?  contains   mail.google.com
  or    fliter   url? conttains  mail.yahoo.com
  and   filter   modulelist? does_not_contain  "mswsock.dll 5.1.2600.3394"


that last example of module list might be a stretch, but would be very
valuable to check module list for existance or non-existance of binary
components and their version numbers.

from there we would want to see the results and export to csv to
import things like url lists into page load testing systems to look
for reproducible crashers.
