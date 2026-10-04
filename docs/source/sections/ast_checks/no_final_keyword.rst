noFinalKeyword
================

Flags use of the ``final`` specifier on classes, structs, and virtual
methods, e.g. ``class Foo final { ... };`` or ``void f() final;``.

.. code-block:: cpp

   class Foo final {};        // Bad — flagged.
   class Foo {};               // Good.

   struct Base { virtual void f(); };
   struct Foo : Base {
       void f() final;         // Bad — flagged.
       void f() override;      // Good.
   };

A parameter or variable merely named ``final`` (a valid, non-reserved
identifier) is not affected — only the class/struct and member-function
virt-specifier positions are checked.

Configuration
--------------

This check takes no configuration.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["noFinalKeyword"]
