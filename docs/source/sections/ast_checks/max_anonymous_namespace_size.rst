maxAnonymousNamespaceSize
=========================

Limits what may live in an anonymous namespace. Everything in it has
internal linkage and cannot be reached from a unit test, so only a few small
helpers belong there; larger code should move to a named (e.g. ``detail``)
namespace.

An anonymous namespace is flagged if it defines any class, struct or union
(including class templates), or if it has more than ``max_declarations``
top-level declarations. Functions, function templates, variables and type
aliases/typedefs count; a function declared and later defined in the same
namespace counts once.

.. code-block:: cpp

   // With max_declarations = 3
   namespace {                 // Bad — defines a struct.
   struct Helper {};
   }

   namespace {                 // Bad — 4 declarations.
   int a();
   int b();
   int c();
   int d();
   }

   namespace {                 // Good.
   constexpr int kSize = 3;
   int twice(int x) { return 2 * x; }
   }

Each ``namespace { ... }`` block is checked on its own and reported once, at
its opening ``namespace`` keyword. Declarations coming from another file
(e.g. an ``#include`` inside the block) are ignored, as are nested
namespaces, ``using`` declarations, ``static_assert`` and forward
declarations of classes.

Configuration
-------------

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 45

   * - Key
     - Type
     - Default
     - Description
   * - ``max_declarations``
     - integer
     - ``3``
     - Maximum number of top-level declarations per anonymous namespace.
       Must be ``>= 0``.

.. code-block:: toml

   [cpp.ast_check_config.maxAnonymousNamespaceSize]
   max_declarations = 5
