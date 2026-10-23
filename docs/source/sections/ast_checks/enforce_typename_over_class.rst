enforceTypenameOverClass
==========================

Flags a template type parameter introduced with ``class`` instead of
``typename``.

.. code-block:: cpp

   template <class T>        // Bad — flagged.
   void f(T t);

   template <typename T>     // Good.
   void f(T t);

Only the keyword in a ``TEMPLATE_TYPE_PARAMETER`` position is checked — a
plain, non-template ``class Foo {};`` declaration is unaffected.

Configuration
--------------

This check takes no configuration.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["enforceTypenameOverClass"]
