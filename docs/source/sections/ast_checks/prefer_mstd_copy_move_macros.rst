preferMstdCopyMoveMacros
========================

Flags copy/move constructors and assignment operators deleted by hand and
suggests the mstd macros ``MSTD_NO_COPY(X)`` and ``MSTD_NO_MOVE(X)``, which
expand to exactly these declarations.

.. code-block:: cpp

   class Foo
   {
       Foo(const Foo &)            = delete;   // Bad — use MSTD_NO_COPY(Foo).
       Foo &operator=(const Foo &) = delete;   // Bad — use MSTD_NO_COPY(Foo).
       Foo(Foo &&)                 = delete;   // Bad — use MSTD_NO_MOVE(Foo).
       Foo &operator=(Foo &&)      = delete;   // Bad — use MSTD_NO_MOVE(Foo).
   };

   class Bar
   {
       MSTD_NO_COPY(Bar)    // Good.
       MSTD_NO_MOVE(Bar)    // Good.
   };

Members produced by any macro expansion (``MSTD_NO_COPY``,
``MSTD_NO_MOVE``, ``MSTD_RAII_NO_MOVE``, ...) are never flagged; only a
``= delete`` written in the file itself is. Defaulted members, other
deleted functions and converting constructors are not affected.

Each member is reported on its own, so deleting only the copy constructor
by hand is flagged as well, even though the macro also deletes the copy
assignment.

Configuration
-------------

.. list-table::
   :header-rows: 1
   :widths: 25 15 20 40

   * - Key
     - Type
     - Default
     - Description
   * - ``copy_macro``
     - string
     - ``"MSTD_NO_COPY"``
     - Macro suggested for deleted copy members.
   * - ``move_macro``
     - string
     - ``"MSTD_NO_MOVE"``
     - Macro suggested for deleted move members.

.. code-block:: toml

   [cpp.ast_check_config.preferMstdCopyMoveMacros]
   copy_macro = "MY_NO_COPY"
   move_macro = "MY_NO_MOVE"

Disabling
---------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["preferMstdCopyMoveMacros"]
