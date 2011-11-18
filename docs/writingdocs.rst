.. index:: writingdocs

.. _writingdocs-chapter:

Writing documentation
=====================

To contribute with your documentation follow these steps to be able to
modify the git repo, build a local copy and deploy on `ReadTheDocs.org`_.


.. _`ReadTheDocs.org`: https://readthedocs.org/


Installing Sphinx
--------------------

`Sphinx`_ is an external tool that compiles these `reStructuredText`_ into
HTML. Since it's a python tool you can install it with
``easy_install`` or ``pip`` like this::

 pip install sphinx


.. _Sphinx: http://sphinx.pocoo.org/
.. _reStructuredText: http://sphinx.pocoo.org/rest.html

Making the HTML
---------------

Now you can build the docs with this simple command::

 cd docs
 make html

This should update the revelant HTML files in ``socorro/docs/_build``
and you can preview it locally like this (on OS X for example)::

 open _build/html/index.html

Making it appear on ReadTheDocs
-------------------------------

`ReadTheDocs.org`_ is wired to build the documentation nightly from
this git repository but if you want to make documentation changes
appear immediately you can use their `webhooks`_ to re-create the
build and update the documentation right away.

.. _webhooks: http://readthedocs.org/docs/read-the-docs/latest/webhooks.html

Or, just send the pull request
------------------------------

If you have a relevant update to the documentation but don't have time
to set up your Sphinx and git environment you can just edit these
files in raw mode and send in a pull request.

Or, just edit the documentation online
--------------------------------------

The simplest way to edit the documentation is to just edit it inside the Github editor. To get started,
go to https://github.com/mozilla/socorro and browse in the `docs <https://github.com/mozilla/socorro/tree/master/docs>`_
directory to find the file you want to edit.

Then click the "Edit this file" button in the upper right-hand corner and type away.

When you're done, write a comment underneath and click "Commit Changes".

If you are unsure about how to edit reStructuredText and don't want to trial-and-error your way through the editing,
then one thing you can do is to copy the text into an `online reStructuredText editor <http://rst.ninjs.org/>`_
and see if you get the syntax right. Obviously you'll receive warnings and errors about broken
internal references but at least you'll know if syntax is correct.

