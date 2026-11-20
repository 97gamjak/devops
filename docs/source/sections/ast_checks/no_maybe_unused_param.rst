noMaybeUnusedParam
==================

Flags ``[[maybe_unused]]`` on function, method, constructor and lambda
parameters. An unused parameter is left unnamed, or keeps its name only as a
comment.

.. code-block:: cpp

   void draw([[maybe_unused]] const Frame &frame);   // Bad — flagged.
   void draw(const Frame &frame [[maybe_unused]]);   // Bad — flagged.
   void draw(const Frame & /*frame*/);               // Good.
   void draw(const Frame &);                         // Good.

``[[maybe_unused]]`` on variables, functions and members is not affected,
nor are other attributes such as ``[[gnu::unused]]``. An attribute that
comes from a macro expansion is not reported.

Configuration
-------------

This check takes no configuration.

Disabling
---------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["noMaybeUnusedParam"]
