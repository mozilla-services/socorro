.. _signaturegeneration-chapter:

====================
Signature Generation
====================

.. contents::
   :local:


Overview
========

When processing a crash report, Socorro generates a *crash signature*. The
signature is a short string that lets us group crash reports that likely have a
common cause together.

Signature generation typically starts with a string based on the stack of the
crashing thread. Various rules are applied that adjust the signature and after
everything is done, we have a Socorro crash signature.

Signature generation is finicky. When it generates too coarse a signature, then
crash reports that have nothing to do with one another end up grouped together.
When it generates too fine a signature, then crash reports end up in very small
groups which are unlikely to be looked at. Since technologies are constantly
changing, we're constantly honing signature generation.

Anyone can suggest changes to signature generation. It's the part of the crash
ingestion pipeline that's maintained by non-Socorro developers.

Signature generation code is here:

https://github.com/mozilla-services/socorro/tree/main/socorro/signature


The lists for configuring the C signature generation class are here:

https://github.com/mozilla-services/socorro/tree/main/socorro/signature/siglists


How to make a signature generation change
=========================================

Signature generation changes are typically self-service. Code reviews and
deployments are handled by the Socorro maintainers, but we ask you to file a
pull request on GitHub with the desired change.

To make a change to signature generation:

`Write up a bug in the Socorro product
<https://bugzilla.mozilla.org/enter_bug.cgi?format=__standard__&product=Socorro&short_desc=[siglist]>`_
and please include the following:

1. explanation of what the problem you want to solve is
2. urls of examples of crashes that have the problem you're trying to solve

Examples of signature generation change bugs:

* https://bugzilla.mozilla.org/show_bug.cgi?id=1397926
* https://bugzilla.mozilla.org/show_bug.cgi?id=1402037

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

This is done by the Socorro maintainers.

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

Note that after a signature change has been pushed to production, it may be
useful to `reprocess the affected signatures <https://github.com/adngdb/reprocess>`_.
We can help with this if the change author requests it.


Philosophy on signature generation
==================================

Signatures should be such that they group like crash reports together. Signatures
that are too coarse or too fine are unhelpful.

We can make changes to signature generation and then reprocess affected crashes.
We often do this to better analyze specific kinds of crashes--maybe to break
up a signature into smaller groups.

Sometimes we make changes to signature generation when focusing on a specific
class of crashes and we tweak signatures so as to highlight interesting things.
Using `siggen <https://github.com/willkg/socorro-siggen/>`_ can make
experimenting easier to do.

When you're adding a symbol to a list so that signature generation will
continue past a certain frame and you're deciding between whether to add a
symbol to the "prefix list" or the "irrelevant list", use the following to help
guide you:

1. If it's a symbol that has platform variants and the symbol isn't helpful
   in summarizing the cause of the crash, then put it in the irrelevant list.

2. If it's a symbol that's part of panic/error/crash handling code that kicks
   off *after* the cause of the crash to handle the crash, then put it in the
   irrelevant list.

3. Otherwise, put it in the prefix list.

If you have questions, please ask in the bug comments.


.. include:: ../socorro/signature/README.rst


.. include:: ../socorro/signature/siglists/README.rst


.. include:: ../socorro/signature/pipeline.rst
