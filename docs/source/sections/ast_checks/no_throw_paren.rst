noThrowParen
==============

Flags ``throw(...)`` where the parentheses wrap the *entire* thrown
expression, e.g. ``throw(x);`` or ``throw(SomeException(1));``. Write these
as ``throw x;`` / ``throw SomeException(1);`` instead.

.. code-block:: cpp

   throw(SomeException(1));  // Bad — flagged, parens wrap the whole throw.
   throw SomeException(1);   // Good.
   throw;                    // Good — a bare rethrow is always allowed.

Parentheses that are only part of the thrown expression itself, such as a
constructor or function call (``throw SomeException(1);``), are not
affected — only parentheses spanning the whole expression are flagged.

Configuration
--------------

This check takes no configuration.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["noThrowParen"]
