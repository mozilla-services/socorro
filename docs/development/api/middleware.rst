.. index:: middleware

.. _middleware-chapter:

Middleware API
==============

The middleware API is deprecated and no longer used.

Instead, the Django view functions instantiate classes from the ``socorro``
package and call their respective instances ``get``, ``post`` or ``put``
methods.
