# Signatures Utilities Lists

This folder contains lists that are used to configure the C signature generation process. Each ``.txt`` file contains a list of signatures or regex matching signatures, that are used at various steps of our algorithm. Regular expressions use the [Python syntax](https://docs.python.org/2/library/re.html#regular-expression-syntax).

## Signature Generation Algorithm

When generating a C signature, 5 steps are involved.

1. We walk the crashing thread's stack, looking for things that would match the [Signature Sentinels](#signature-sentinels). The first matching element, if any, becomes the top of the sub-stack we'll consider going forward.
2. We walk the stack, ignoring everything that matches the [Irrelevant Signatures](#irrelevant-signatures). We consider the first non-matching element the top of the new sub-stack.
3. We rewrite every signature missing symbols that matches the [Trim DLL Signatures](#trim-dll-signatures) to be the module only (the part before the first ``@`` sign). We also merge them so only one of those frames makes it to the final signature.
4. We accumulate signatures that match the [Prefix Signatures](#prefix-signatures), until something doesn't match.
5. We normalize each signature we accumulated. Signatures that match the [Signatures With Line Numbers](#signatures-with-line-numbers) have their associated code line number added to them, like this: ``signature:42``.

The generated signature is a concatenation of all the accumulated signatures, separated with a pipe sign (`` | ``).

## Signature Sentinels

File: [``signature_sentinels.txt``](./signature_sentinels.txt)

Signature Sentinels are signatures (not regular expression) that should be used as the top of the stack if present. Everything before the first matching signature will be ignored.

## Irrelevant Signatures

File: [``irrelevant_signature_re.txt``](./irrelevant_signature_re.txt)

Irrelevant Signatures are regular expressions of signatures that will be ignored while going through the stack. Anything that matches this list will not be added to the overall signature.

## Prefix Signatures

File: [``prefix_signature_re.txt``](./prefix_signature_re.txt)

Prefix Signatures are regular expressions of signatures that will be combined with the following frame's signature. Signature generation stops at the first non-matching signature it finds.

## Trim DLL Signatures

File: [``trim_dll_signature_re.txt``](./trim_dll_signature_re.txt)

Trim DLL Signatures are regular expressions of signatures that will be trimmed down to only their module name. For example, if the list contains ``foo32\.dll.*`` and a stack trace looks like this:

<pre>0x0
foo32.dll@0x2131
foo32.dll@0x1943
myFavoriteSig()
</pre>

The generated signature will be: ``0x0 | foo32.dll | myFavoriteSig()``.

## Signatures With Line Numbers

File: [``signatures_with_line_numbers_re.txt``](./signatures_with_line_numbers_re.txt)

Signatures with line number are regular expressions of signatures that will be combined with their associated source code line numbers.

## How to edit these lists

The first thing we will ask you to do is to file a bug. We keep track of every change in Socorro via bugs, so it's important that each commit has one associated to it. File a bug in the [Socorro::General component](https://bugzilla.mozilla.org/enter_bug.cgi?product=Socorro&component=General), describe the changes you want to make, and assign it to you.

Then proceed to making those changes...

### Using the command line

If you are a git power user, you probably don't need us to explain how to do this! :)

If you are not, you're probably better off using GitHub's interface. Read on!

### Using GitHub's interface

First, you need to be logged in to GitHub. Open the file you want to edit, and then click the little pen in the top right corner of the page, the one that says ``Fork this project and edit the file``, or ``Edit the file in your fork of this project`` if you already have a fork of it.

That will take you to an editor, where you can write any changes you want. Once you are done editting the file, enter a commit description. We have some conventions, and a bot that will automatically close bugs, so please make your commit message following this pattern: ``Fixes bug XYZ - Desciption of the change``. Once you are ready, click ``Propose file change``.

That will create a branch in your fork of the socorro project, and take you to the commit you just created. You can verify that the changes you made are correct, and then click ``Create pull request``, and then ``Create pull request`` again. Once the pull request is opened, [travis](https://travis-ci.org/mozilla/socorro) will automatically start running our test suite, which includes sanity checks for those signature lists. You can see the status of those tests in the pull request, and click the ``Details`` link to see logs in case of a failure.

---

That's it! You have proposed a change, we have been notified about it. Someone from the Socorro team will review your changes and merge them if they are appropriate. Thank you for contributing to Socorro!

## Watching only the siglists folder

If you are interested in watching what's changing in this ``siglists`` folder, but don't care much about what happens in the rest of the Socorro repo, you can easily set a filter in your email client to do that. Here's an example filter you can use today:

<pre>to:(socorro@noreply.github.com) ("A socorro/siglists/" OR "M socorro/siglists/" OR "D socorro/siglists")</pre>
