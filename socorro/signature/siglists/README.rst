Signatures Utilities Lists
==========================

This folder contains lists that are used to configure the C signature generation
process. Each ``.txt`` file contains a list of signatures or regex matching
signatures, that are used at various steps of our algorithm. Regular expressions
use the `Python syntax
<https://docs.python.org/3.7/library/re.html#regular-expression-syntax>`_.


Signature Generation Algorithm
------------------------------

When generating a C/Rust signature, 5 steps are involved.

1. We walk the crashing thread's stack, looking for things that would match the
   `Signature Sentinels <#signature-sentinels>`_. The first matching element, if
   any, becomes the top of the sub-stack we'll consider going forward.
2. We walk the stack, ignoring everything that matches the `Irrelevant
   Signatures <#irrelevant-signatures>`_. We consider the first non-matching
   element the top of the new sub-stack.
3. We rewrite dll frame signatures to be the module only and merge consecutive
   ones.
4. We accumulate signatures that match the `Prefix Signatures
   <#prefix-signatures>`_, until something doesn't match.
5. We normalize each signature we accumulated. Signatures that match the
   `Signatures With Line Numbers <#signatures-with-line-numbers>`_ have their
   associated code line number added to them, like this: ``signature:42``.

The generated signature is a concatenation of all the accumulated signatures,
separated with a pipe sign (``|``), and converted to a regular expression.

Signature generation then uses ``.match()`` to match frames.

Because of that, when changing these lists, make sure you keep the following
things in mind:

1. Make sure you're using valid regular expression syntax and escape special
   characters like ``(``, ``)``, ``.``, and ``$``.
2. There's no need to add a trailing ``.*`` since signature generation uses
   ``.match()`` which will match from the beginning of the string.
3. Try to keep it roughly in alphabetical order so as to make it easier to skim
   through later.


Signature Sentinels
~~~~~~~~~~~~~~~~~~~

File: ``signature_sentinels.txt``

Signature Sentinels are signatures (not regular expression) that should be used
as the top of the stack if present. Everything before the first matching
signature will be ignored.

The code iterates through the stack frame, throwing away everything it finds
until it encounters a match to this regular expression or the end of the stack.
If it finds a match, it passes all the frames after the match to the next step.
If it finds no match, it passes the whole list of frames to the next step.

A typical line might be ``_purecall``.


Prefix Signatures
~~~~~~~~~~~~~~~~~

File: ``prefix_signature_re.txt``

Prefix Signatures are regular expressions of signatures that will be combined
with the following frame's signature. Signature generation stops at the first
non-matching signature it finds.

A typical rule might be ``JSAutoCompartment::JSAutoCompartment.*``.

.. Note::

   These are regular expressions. Dollar signs and other regexp characters need
   to be escaped with a ``\``.


Irrelevant Signatures
~~~~~~~~~~~~~~~~~~~~~

File: ``irrelevant_signature_re.txt``

Irrelevant Signatures are regular expressions of signatures that will be
ignored while going through the stack. Anything that matches this list will not
be added to the overall signature.

Add symbols to this list that:

1. have platform variants that prevent crash signatures from being the same
   across platforms
2. are involved in panic, error, or crash handling code that happens *after*
   the actual crash

A typical rule might be ``(Nt|Zw)?WaitForSingleObject(Ex)?``.


Signatures With Line Numbers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

File: ``signatures_with_line_numbers_re.txt``

Signatures with line number are regular expressions of signatures that will be
combined with their associated source code line numbers.
