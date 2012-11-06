.. index:: throttling

.. _throttling-chapter:

Throttling
==========

The :ref:`collector-chapter` has the ability to vet crashes as the come into
the system. Originally, this system was used to provide a statistical
sampling from the incoming stream of crashes. In 1.8, throttling is a
way to allow a sampling of crashes to be put into the database.

Throttling, the disposition of a JSON/dump pair, is controlled by the
contents of the JSON file. The JSON files are collections of keys and
values. :ref:`collector-chapter` can examine these key/value pairs and assign
a pass through probability. For example we may want to pass 100% of
all alpha or beta releases to the database. In production, however, we
may want to only save 10%.

For details on how to configure throtttling, see the configuration
section of :ref:`collector-chapter`. Below is a section about the collector
throttling rules.


throttleConditions
------------------

This option tells the collector how to route a given JSON/dump pair to
storage for further processing or deferred storage. This consists of a
list of conditions in this form: (RawCrashKey?, ConditionFunction?,
Probability)

* RawCrashKey?: a name of a field from the HTTP POST form. The
  possibilities are: "StartupTime?", "Vendor", "InstallTime?",
  "timestamp", "Add-ons", "BuildID", "SecondsSinceLastCrash?", "UserID",
  "ProductName?", "URL", "Theme", "Version", "CrashTime?"
  Alternatively, the string "*" has special meaning when the
  ConditionFunction? is a reference to a Python function.
* ConditionFunction?: a function accepting a single string value and
  returning a boolean; regular expression; or a constant used for an
  equality test with the value for the RawCrashKey?.
  Alternatively, If the RawCrashKey? is "*" and the function will be
  passed the entire raw crash as a dict rather than just a single
  value of one element of the raw crash.
* Probability: an integer between 0 and 100 inclusive. At 100, all
  JSON files, for which the ConditionFunction? returns true, will be
  saved in the database. At 0, no JSON files for which the
  ConditionFunction? returns true will be saved to the database. At 25,
  there is twenty-five percent probability that a matching JSON file
  will be written to the database.
  Alternatively, the value can be None.  In that case, no probablity is
  calculated and the throttler just returns the IGNORE value.  The crash
  is not stored and "Unsupported=1" is returned to the client.

There must be at least one entry in the throttleConditions list. The
example below shows the default case.

These conditions are applied one at a time to each submitted crash.
The first match of a condition function to a value stops the iteration
through the list. The probability of that first matched condition will
be applied to that crash.

Keep the list short to avoid bogging down the collector.::

 throttleConditions = cm.Option()
 throttleConditions.default = [
   #("Version", lambda x: x[-3:] == "pre", 25), # queue 25% of crashes with version ending in "pre"
   #("Add-ons", re.compile('inspector\@mozilla\.org\:1\..*'), 75), # queue 75% of crashes where the inspector addon is at 1.x
   #("UserID", "d6d2b6b0-c9e0-4646-8627-0b1bdd4a92bb", 100), # queue all of this user's crashes
   #("SecondsSinceLastCrash", lambda x: 300 >= int(x) >= 0, 100), # queue all crashes that happened within 5 minutes of another crash
   ("*", lambda d: d["Product"] == "Flock" and d["Version"] == "3.0", None), # ignore Flock 3.0
   (None, True, 10) # queue 10% of what's left
 ]
