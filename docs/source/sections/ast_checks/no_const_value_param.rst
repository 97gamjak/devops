noConstValueParam
=================

Flags a named by-value parameter declared with top-level ``const``. A
by-value parameter is a local copy, so the ``const`` is not part of the
function's interface and only adds noise.

.. code-block:: cpp

   void f(const int x) {}          // Bad — flagged.
   void f(int x) {}                // Good.

   void g(int *const p) {}         // Bad — the pointer itself is const.
   void g(const int *p) {}         // Good — pointer to const.

   void h(const Foo &foo) {}       // Good — reference.
   void h(Foo &&foo) {}            // Good — rvalue reference.

   auto l = [](const double d) {}; // Bad — lambdas are checked too.

clang-tidy's ``readability-avoid-const-params-in-decls`` only covers
declarations; this check covers definitions as well as declarations.

Not flagged:

- unnamed parameters (``void f(const int);``),
- parameters of ``= delete``\ d or ``= default``\ ed functions,
- ``const`` coming from a type alias (``using CInt = const int;``) or from a
  macro expansion, since it cannot be dropped at the parameter itself,
- parameters inside function types, e.g. function pointers.

Configuration
--------------

This check takes no configuration.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["noConstValueParam"]
