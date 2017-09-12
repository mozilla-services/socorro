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

https://github.com/mozilla-services/socorro/tree/master/socorro/signature



.. include:: ../../socorro/signature/README.rst


.. include:: ../../socorro/siglists/README.rst
