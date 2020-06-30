.. _signaturegeneration-chapter:

====================
Signature Generation
====================

.. contents::


Introduction
============

During processing of a crash, Socorro creates a signature using the signature
generation module. Signature generation typically starts with a string based
on the stack of the crashing thread. Various rules are applied and after everything
is done, we have a Socorro crash signature.

The signature generation code is here:

https://github.com/mozilla-services/socorro/tree/main/socorro/signature


The lists for configuring the C signature generation class are here:

https://github.com/mozilla-services/socorro/tree/main/socorro/signature/siglists


How to request a change to signature generation
===============================================

To request a change to signature generation:

`Write up a bug in the Socorro product
<https://bugzilla.mozilla.org/enter_bug.cgi?format=__standard__&product=Socorro&short_desc=[siglist]>`_
and please include the following:

1. explanation of what the problem you want to solve is
2. urls of examples of crashes that have the problem you're trying to solve
3. expected signatures for those crashes

We need this to make sure we can help you make the right changes.

Examples of bugs:

* https://bugzilla.mozilla.org/show_bug.cgi?id=1397926
* https://bugzilla.mozilla.org/show_bug.cgi?id=1402037


How to make a signature generation change
=========================================

If you've made changes to signature generation before or you're confident in
the change you're making, you can make changes directly using the GitHub
interface:

https://github.com/mozilla-services/socorro/tree/main/socorro/signature/siglists

If you want to test your changes or experiment with them, then you'll need to
set up a local development environment and make the changes with a GitHub
pull request.

See :ref:`localdevenv-chapter` for setting up a local development environment.

Read through the rest of this chapter which describes how signature generation
works, what files are involved, and how to test changes.


How to review a signature generation changes
============================================

1. Make sure the PR has a corresponding bug in Bugzilla and references the bug
   in the commit summary.

   This is important because signature generation is tricky and we need the
   historical data for what changes we made, for whom, why, and how it affected
   signature generation.

2. Verify there are no typos in the change.

   We have a unit test that verifies there are no syntax errors in those files,
   but that (obviously) doesn't cover typos.

3. Run the pull request changes through signature generation using the command line
   interface in your local dev environment. See :ref:`signaturegeneration-chapter-module`.

4. Verify with the author that the changes occur as intended.

5. Merge the PR and verify the example crashes on -stage.

The easiest way to do that is to use Super Search and search for a signature.
The most common change is an addition to the prefix list, in which case you want
to search for the frame signature that was added, and verify that in recent
signatures there is something following it.

If you don't want to wait for new crash reports to arrive, you can find an
existing one and send it to reprocessing. That can be done on the report/index
page directly, or via the admin panel.

Note that after a signature change has been pushed to production, you might want
to `reprocess the affected signatures <https://github.com/adngdb/reprocess>`_.


.. include:: ../socorro/signature/README.rst


.. include:: ../socorro/signature/siglists/README.rst


.. include:: ../socorro/signature/pipeline.rst
