======
How to
======

Processing requests for memory dumps and private user data access
=================================================================

People file bugs in Bugzilla asking to be granted access to memory dumps
and private user data using
`these instructions <https://crash-stats.mozilla.org/documentation/memory_dump_access/>`_.

Process for handling those:

1. Check to see if they're a Mozilla employee. If they aren't, then we can't
   grant them access.

2. Make sure they've logged into Crash Stats prod. If they have, there will be a
   user account with their LDAP username.

3. Look them up in phonebook and find their manager.

4. Reply in the bug asking the reporter to agree to the memory dump access
   agreement. Make sure to copy and paste the terms in the bug comments as well
   as the url to where it exists. Tag the reporter with a needinfo.

5. Reply in the bug asking the manager to verify the reporter requires access to
   PII on Crash Stats for their job. Tag the manager with a needinfo.

Then wait for those needinfos to be filled. Once that's done:

1. Log into Crash Stats.
2. Go into the admin.
3. Look up the user.
4. Add the user to the "Hackers" group.

Then reply in the bug something like this::

    You have access to memory dumps and private user data on Crash Stats. You
    might have to log out and log back in again. Let us know if you have any
    problems!

    Thank you!

and mark the bug FIXED.

That's it!
