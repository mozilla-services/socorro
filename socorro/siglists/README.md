# Signatures Utilities Lists

This folder contains lists that are used to configure the C signature generation process. Each ``.txt`` file contains a list of signatures or regex matching signatures, that are used at various steps of our algorithm.

## Signature Generation Algorithm

When generating a C signature, 4 steps are involved.

1. We walk the crashing thread's stack, looking for things that would match the [signature sentinels](#signature-sentinels). The first matching element, if any, becomes the top of the sub-stack we'll consider going forward.
2. We walk the stack, ignoring everything that matches the [irrelevant signatures](#irrelevant-signatures). We consider the first non-matching element the top of the new sub-stack.
3. We accumulate signatures that match the [prefix signatures](#prefix-signatures), until something doesn't match.
4. We normalize each signature we accumulated. Signatures that match the [signatures with line numbers](#signatures-with-line-numbers) have their associated code line number added to them, like this: ``signature:42``.

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

## Signatures With Line Numbers

File: [``signatures_with_line_numbers_re.txt``](./signatures_with_line_numbers_re.txt)

Signatures with line number are regular expressions of signatures that will be combined with their associated source code line numbers.

## How to edit these lists

The first thing we will ask you to do is to file a bug. We keep track of every change in Socorro via bugs, so it's important that each commit has one associated to it. File a bug in the [Socorro::General component](https://bugzilla.mozilla.org/enter_bug.cgi?product=Socorro&component=General), describe the changes you want to make, and assign it to you.

Then proceed to making those changes...

### Using command lines

If you are a git power user, you probably don't need us to explain how to do this! :)

If you are not, you're probably better of using github's interface. Read on!

### Using github's interface

First, you need to be logged in to github. Open the file you want to edit, and then click the little pen in the top right corner of the page, the one that says ``Fork this project and edit the file``, or ``Edit the file in your fork of this project`` if you already have a fork of it.

That will take you to an editor, where you can write any changes you want. Once you are done editting the file, enter a commit description. We have some conventions, and a bot that will automatically close bugs, so please make your commit message following this pattern: ``Fixes bug XYZ - Desciption of the change``. Once you are ready, click ``Propose file change``.

That will create a branch in your fork of the socorro project, and take you to the commit you just created. You can verify that the changes you made are correct, and then click ``Create pull request``, and then ``Create pull request`` again. Once the pull request is opened, travis will automatically start running our test suite, which includes sanity checks for those signature lists. You can see the status of those tests in the pull request, and click the ``Details`` link to see logs in case of a failure.

---

That's it! You have proposed a change, we have been notified about it. Someone from the Socorro team will review your changes and merge them if they are appropriate. Thank you for contributing to Socorro!
